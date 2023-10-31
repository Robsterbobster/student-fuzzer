import ast

NAME = 'entrypoint'


class FunctionFinder(ast.NodeVisitor):
    def __init__(self):
        self.function_name = NAME
        self.function_node = None

    def visit_FunctionDef(self, node):
        if node.name == self.function_name:
            self.function_node = node


class LafIntelTransformer(ast.NodeTransformer):
    def visit_If(self, node):
        # inspect if
        condition = node.test
        # Recursively visit the body of the if statement
        if node.body:
            body = []
            for stmt in node.body:
                body.append(self.visit(stmt))
            node.body = body

        if node.orelse:
            orelse = []
            for stmt in node.orelse:
                orelse.append(self.visit(stmt))
            node.orelse = orelse

        if self.check_integer_comparison(condition):
            # Todo: Have bugs when multi-conditions
            # node = self.transformGEQLEQ(node)
            # node = self.split_compares_pass(node)
            pass
        elif self.check_string_comparison(condition, False):
            splitted_node = self.compare_transform_pass(node, node.test, node.body)
            if len(node.orelse) > 0:
                else_node = ast.If(test=ast.UnaryOp(op=ast.Not(), operand=node.test), body=node.orelse, orelse=[])
                splitted_else_node = self.compare_transform_pass(else_node, else_node.test, else_node.body) if \
                    self.check_string_comparison(else_node.test, False) else [else_node]
                splitted_node.extend(splitted_else_node)
            return splitted_node
        return node

    """
        We assume string comparison has two operands and one operator
    """

    def check_string_comparison(self, condition, not_indicator):
        if isinstance(condition, ast.Compare):
            if (isinstance(condition.ops[0], ast.Eq) and not not_indicator) or \
                    (isinstance(condition.ops[0], ast.NotEq) and not_indicator):
                return self.check_atomic_string_comparison(condition)
        elif isinstance(condition, ast.BoolOp):
            for expr in condition.values:
                if self.check_string_comparison(expr, not_indicator):
                    return True
        elif isinstance(condition, ast.UnaryOp):
            return self.check_string_comparison(condition.operand, not not_indicator)
        return False

    def check_atomic_string_comparison(self, condition: ast.Compare):
        left = condition.left
        if isinstance(left, ast.Str):
            if not (isinstance(condition.comparators[0], ast.Str) or
                    isinstance(condition.comparators[0], ast.Num)):
                return True
        elif not isinstance(left, ast.Num):
            if isinstance(condition.comparators[0], ast.Str):
                return True
        return False

    """
        We assume integer comparison has two operands and one operator
    """

    def check_integer_comparison(self, condition):
        if isinstance(condition, ast.Compare):
            left = condition.left
            if isinstance(left, ast.Num) and isinstance(left.n, int):
                if not (isinstance(condition.comparators[0], ast.Str) or
                        isinstance(condition.comparators[0], ast.Num)):
                    return True
            elif not isinstance(left, ast.Str):
                if isinstance(condition.comparators[0], ast.Num) \
                        and isinstance(condition.comparators[0].n, int):
                    return True
        return False

    """
    For integer comparison, we transform a <= b to a < b or a == b,
    a >= b to a > b or a == b
    """

    def transformGEQLEQ(self, node):
        condition = node.test
        if isinstance(condition, ast.Compare):
            new_compares = []
            for i, op in enumerate(condition.ops):
                new_compare_vals = []
                # this array disjuncts the < and == condition
                if isinstance(op, ast.GtE):
                    new_compare_vals.append(
                        ast.Compare(left=condition.left if i == 0 else condition.comparators[i - 1], ops=[ast.Gt()],
                                    comparators=[condition.comparators[i]]))
                    new_compare_vals.append(
                        ast.Compare(left=condition.left if i == 0 else condition.comparators[i - 1], ops=[ast.Eq()],
                                    comparators=[condition.comparators[i]]))
                    new_compares.append(ast.BoolOp(op=ast.Or(), values=new_compare_vals))
                elif isinstance(op, ast.LtE):
                    new_compare_vals.append(
                        ast.Compare(left=condition.left if i == 0 else condition.comparators[i - 1], ops=[ast.Lt()],
                                    comparators=[condition.comparators[i]]))
                    new_compare_vals.append(
                        ast.Compare(left=condition.left if i == 0 else condition.comparators[i - 1], ops=[ast.Eq()],
                                    comparators=[condition.comparators[i]]))
                    new_compares.append(ast.BoolOp(op=ast.Or(), values=new_compare_vals))
                else:
                    new_compares.append(
                        ast.Compare(left=condition.left if i == 0 else condition.comparators[i - 1], ops=[op],
                                    comparators=[condition.comparators[i]]))
            new_node = ast.BoolOp(op=ast.And(), values=new_compares)
            # this conjuncts all the rewritten conditions that are in the form of (a < b or a == b)
            node.test = new_node
            return node
        return node

    def compare_transform_pass(self, node, condition, node_body):
        if isinstance(condition, ast.Compare):
            return [self.atomic_compare_transform_pass(node, condition, node_body)]
        elif isinstance(condition, ast.BoolOp):
            non_str_exprs = []
            nested_if_body = node_body
            nested_if_nodes = []
            for expr in condition.values:
                if self.check_string_comparison(expr, False):
                    # If the a or b or c, we convert it into multiple ifs
                    if isinstance(condition.op, ast.Or):
                        nested_if_nodes.extend(self.compare_transform_pass(node, expr, nested_if_body))
                    else:
                        # otherwise we do nested ifs
                        nested_if_nodes = self.compare_transform_pass(node, expr, nested_if_body)
                    nested_if_body = nested_if_nodes if isinstance(condition.op, ast.And) else node_body
                else:
                    non_str_exprs.append(expr)
            if len(non_str_exprs) > 0:
                new_node = ast.If(test=ast.BoolOp(op=condition.op, values=non_str_exprs), body=nested_if_nodes,
                                  orelse=[] if isinstance(condition.op, ast.And) else nested_if_nodes)
                return [new_node]
            return nested_if_nodes
        elif isinstance(condition, ast.UnaryOp):
            if isinstance(condition.operand, ast.Compare):
                return [self.atomic_compare_transform_pass(node, condition, node_body)]
            # breaks the bracket
            elif isinstance(condition.operand, ast.BoolOp):
                exprs = []
                for expr in condition.operand.values:
                    exprs.append(ast.UnaryOp(op=condition.op, operand=expr))
                simplified_node = ast.BoolOp(op=ast.And() if isinstance(condition.operand.op, ast.Or) else ast.Or()
                                             , values=exprs)
                condition = simplified_node
                return self.compare_transform_pass(node, condition, node_body)
            # simplify if there are two not
            elif isinstance(condition.operand, ast.UnaryOp) and isinstance(condition.op, ast.Not) \
                    and isinstance(condition.operand.op, ast.Not):
                return self.compare_transform_pass(node, condition.operand.operand, node_body)
        return node

    """
    if a == "abcd"
        TO
    if len(a) > 0 and a[0] == 'a':
        ...
        if len(a) > 3 and a[3] == 'd':
            if len(a) == 4:
                do_something()
            else:
                raise UserWarning(str(len(q) - 4))
    """

    def atomic_compare_transform_pass(self, node, condition, node_if_true):
        compare_condition = condition
        if isinstance(condition, ast.UnaryOp):
            compare_condition = condition.operand
        if isinstance(compare_condition, ast.Compare):
            op = compare_condition.ops[0]
            left = compare_condition.left
            right = compare_condition.comparators[0]
            str_value = ""
            variable = None
            if_conditions = []
            if isinstance(left, ast.Str):
                str_value = left.value
                variable = right
            elif isinstance(right, ast.Str):
                str_value = right.value
                variable = left
            len_call = ast.Call(
                func=ast.Name(id='len', ctx=ast.Load()),
                args=[variable],
                keywords=[]
            )
            for i in range(len(str_value)):
                # len(s) > i
                len_GT_check = ast.Compare(left=len_call, ops=[ast.Gt()], comparators=[ast.Num(n=i)])
                var_idx = ast.Subscript(
                    value=variable,
                    slice=ast.Index(value=ast.Num(n=i)),
                    ctx=ast.Load()
                )
                # s[i] == c
                char_check = ast.Compare(left=var_idx, ops=[ast.Eq()], comparators=[ast.Str(value=str_value[i])])
                if_cond = ast.BoolOp(op=ast.And(), values=[len_GT_check, char_check])
                if_conditions.append(if_cond)
            # len(s) == len(string)
            len_check = ast.Compare(left=len_call, ops=[ast.Eq()], comparators=[ast.Num(n=len(str_value))])
            difference = ast.BinOp(left=len_call, op=ast.Sub(), right=ast.Num(n=len(str_value)))
            difference_str = ast.Call(func=ast.Name(id='str', ctx=ast.Load()), args=[difference], keywords=[])
            # raise UserWarning(str(len(s) - len(string)))
            raise_instruction = ast.Raise(
                exc=ast.Call(func=ast.Name(id='UserWarning', ctx=ast.Load()), args=[difference_str], keywords=[]),
                cause=None)
            len_check_statement = ast.If(
                test=len_check,
                body=node_if_true,
                orelse=[raise_instruction]
            )
            prev_body = [len_check_statement]
            top_if = None
            for i in range(len(str_value) - 1, -1, -1):
                if_statement = ast.If(
                    test=if_conditions[i],
                    body=prev_body,
                    orelse=[]
                )
                prev_body = [if_statement]
                if i == 0:
                    top_if = if_statement
            return top_if
        return node

    """
    For an integer compare, we will create nested if statements
    We assume that python integer is represented by 32 bits, we 
    create nested ifs that does 2-bytewise comparison
    """

    def split_compares_pass(self, node):
        condition = node.test
        if isinstance(condition, ast.Compare):
            for i, op in enumerate(condition.ops):
                if isinstance(op, ast.Eq) or isinstance(op, ast.NotEq):
                    for j, comparator in enumerate(condition.comparators):
                        if_conditions = []
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(left=condition.left, op=ast.RShift(), right=ast.Num(n=24)),
                            ops=[op],
                            comparators=[ast.BinOp(left=comparator, op=ast.RShift(), right=ast.Num(n=24))]
                        ))
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(
                                left=ast.BinOp(left=condition.left, op=ast.BitAnd(), right=ast.Num(n=0xFF0000)),
                                op=ast.RShift(), right=ast.Num(n=16)),
                            ops=[op],
                            comparators=[
                                ast.BinOp(left=ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF0000))
                                          , op=ast.RShift(), right=ast.Num(n=16))]
                        ))
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(left=ast.BinOp(left=condition.left, op=ast.BitAnd(), right=ast.Num(n=0xFF00))
                                           , op=ast.RShift(), right=ast.Num(n=8)),
                            ops=[op],
                            comparators=[
                                ast.BinOp(left=ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF00))
                                          , op=ast.RShift(), right=ast.Num(n=8))]
                        ))
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(left=condition.left, op=ast.RShift(), right=ast.Num(n=0xFF)),
                            ops=[op],
                            comparators=[ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF))]
                        ))
                        prev_body = node.body
                        initial_or_else = node.orelse
                        for i in range(3, -1, -1):
                            if_statement = ast.If(
                                test=if_conditions[i],
                                body=prev_body,
                                orelse=[]
                            )
                            prev_body = [if_statement]
                            if i == 0:
                                node = if_statement
                                node.orelse = initial_or_else
                        return node
        return node


f = open('abug.py', 'r')
content = f.read()
f.close()
parsed_ast = ast.parse(content)
finder = FunctionFinder()
transformer = LafIntelTransformer()
finder.visit(parsed_ast)
function_node = finder.function_node

finder.function_node = transformer.visit(function_node)
modified_code = ast.unparse(parsed_ast)
f = open('modified_bug.py', 'w')
f.write(modified_code)
f.close()
