import ast
from copy import copy

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

        if self.check_string_comparison(condition, False):
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
        We assume integer comparison has two operands and one operator,
        we will not handle the compare of NEQ
    """

    def check_integer_comparison(self, condition, not_indicator):
        if isinstance(condition, ast.Compare):
            if not (isinstance(condition.ops[0], ast.Eq) and not_indicator) and \
                    not (isinstance(condition.ops[0], ast.NotEq) and not not_indicator):
                return self.check_atomic_integer_comparison(condition)
        elif isinstance(condition, ast.BinOp):
            if self.check_integer_comparison(condition.left, not_indicator) or \
                    self.check_integer_comparison(condition.right, not_indicator):
                return True
        elif isinstance(condition, ast.BoolOp):
            for expr in condition.values:
                if self.check_integer_comparison(expr, not_indicator):
                    return True
        elif isinstance(condition, ast.UnaryOp):
            return self.check_integer_comparison(condition.operand, not not_indicator)
        return False

    """
    We avoid split for constant comparison
    """

    def check_atomic_integer_comparison(self, condition: ast.Compare):
        left = condition.left
        if self.check_is_integer(condition.left):
            if not (isinstance(condition.comparators[0], ast.Str) or
                    self.check_is_integer(condition.comparators[0])):
                return True
        elif not isinstance(left, ast.Str):
            if self.check_is_integer(condition.comparators[0]):
                return True
        return False

    def check_is_integer(self, node):
        if (isinstance(node, ast.Num) or isinstance(node, ast.Constant)) and \
                isinstance(node.n, int):
            return True
        elif isinstance(node, ast.UnaryOp) and (isinstance(node.op, ast.USub) or isinstance(node.op, ast.UAdd)):
            return self.check_is_integer(node.operand)
        return False

    def get_integer(self, node):
        if (isinstance(node, ast.Num) or isinstance(node, ast.Constant)) and \
                isinstance(node.n, int):
            return node.n
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -1 * self.get_integer(node.operand)
            elif isinstance(node.op, ast.UAdd):
                return self.get_integer(node.operand)
        return None
    """
    For integer comparison, we transform a <= b to a < b or a == b,
    a >= b to a > b or a == b
    """

    def transformGEQLEQ(self, condition):
        if isinstance(condition, ast.Compare):
            condition = self.atomic_transformGEQLEQ(condition)
        elif isinstance(condition, ast.BinOp):
            if self.check_integer_comparison(condition.left, False):
                condition.left = self.transformGEQLEQ(condition.left)
            if self.check_integer_comparison(condition.right, False):
                condition.right = self.transformGEQLEQ(condition.right)
        elif isinstance(condition, ast.BoolOp):
            for i, expr in enumerate(condition.values):
                if self.check_integer_comparison(expr, False):
                    condition.values[i] = self.transformGEQLEQ(expr)
        elif isinstance(condition, ast.UnaryOp):
            condition.operand = self.transformGEQLEQ(condition.operand)
        return condition

    """
    We make the assumption that a compare is formed by one 
    operator and two operands
    """

    def atomic_transformGEQLEQ(self, condition: ast.Compare):
        op = condition.ops[0]
        new_compare_vals = []
        # this array disjuncts the < and == condition
        if isinstance(op, ast.GtE) or isinstance(op, ast.LtE):
            new_compare_vals.append(
                ast.Compare(left=condition.left, ops=[ast.Gt()] if isinstance(op, ast.GtE) else [ast.Lt()],
                            comparators=[condition.comparators[0]]))
            new_compare_vals.append(
                ast.Compare(left=condition.left, ops=[ast.Eq()],
                            comparators=[condition.comparators[0]]))
            return ast.BoolOp(op=ast.Or(), values=new_compare_vals)
        else:
            return condition

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
            if isinstance(condition.operand, ast.Compare) and self.check_string_comparison(condition, False):
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
        return [node]

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

    def split_compares_pass(self, node, condition, node_body):
        if isinstance(condition, ast.Compare):
            return [self.atomic_split_compare_pass(node, condition, node_body)]
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
    First we compare the sign, then based on the sign we
    split into nested ifs
    eg1. a > -100 TO
    if int(a >= 0) == 0:
        if -a >> somebits < 100 >> somebits:
            if_true_part
    else:
        if_true_part
    
    eg2. a < -100 TO
    if int(a >= 0) == 0:
        if -a >> somebits > 100 >> somebits:
            if_true_part
    
    eg3. a > 100 TO
    if int(a >= 0) == 1:
        if a >> somebits > 100 >> somebits:
            if_true_part
    
    eg4. a < 100 TO
    if int(a >= 0) == 1:
        if a >> somebits < 100 >> somebits:
            if_true_part
    else:
        if_true_part
    """

    def atomic_split_compare_pass(self, node, condition, node_if_true):
        if isinstance(condition, ast.Compare):
            original_op = condition.ops[0]
            op = condition.ops[0]
            left = condition.left
            right = condition.comparators[0]
            value = 0
            variable = None
            if_conditions = []
            if self.check_is_integer(left):
                value = self.get_integer(left)
                variable = right
            elif self.check_is_integer(right):
                value = self.get_integer(right)
                variable = left
            sign = int(value >= 0)
            # construct sign comparison
            int_call = ast.Call(
                func=ast.Name(id='int', ctx=ast.Load()),
                args=[ast.Compare(left=variable, ops=[ast.GtE()], comparators=[ast.Num(n=0)])],
                keywords=[]
            )
            sign_comp = ast.If(test=ast.Compare(left=int_call, ops=[ast.Eq()], comparators=[ast.Num(n=sign)]),
                               body=[], orelse=[])
            # if the value is negative, we will construct nested if condition for when
            # variable is also negative
            if not sign:
                value = -value
                if isinstance(op, ast.Gt):
                    op = ast.Lt()
                elif isinstance(op, ast.Lt):
                    op = ast.Gt()
                variable = ast.UnaryOp(op=ast.USub(), operand=variable)
            value_ast = ast.Num(n=value)
            if_conditions.append(ast.Compare(
                left=ast.BinOp(left=variable, op=ast.RShift(), right=ast.Num(n=56)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[ast.BinOp(left=value_ast, op=ast.RShift(), right=ast.Num(n=56))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF0000000000)),
                    op=ast.RShift(), right=ast.Num(n=48)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[
                    ast.BinOp(left=ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF0000000000))
                              , op=ast.RShift(), right=ast.Num(n=48))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF00000000)),
                    op=ast.RShift(), right=ast.Num(n=40)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[
                    ast.BinOp(left=ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF00000000))
                              , op=ast.RShift(), right=ast.Num(n=40))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF000000)),
                    op=ast.RShift(), right=ast.Num(n=32)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[
                    ast.BinOp(left=ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF000000))
                              , op=ast.RShift(), right=ast.Num(n=32))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF0000)),
                    op=ast.RShift(), right=ast.Num(n=24)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[
                    ast.BinOp(left=ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF0000))
                              , op=ast.RShift(), right=ast.Num(n=24))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(
                    left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF00)),
                    op=ast.RShift(), right=ast.Num(n=16)),
                ops=[ast.Eq() if (isinstance(op, ast.Lt) or isinstance(op, ast.Gt)) else op],
                comparators=[
                    ast.BinOp(left=ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF00))
                              , op=ast.RShift(), right=ast.Num(n=16))]
            ))
            if_conditions.append(ast.Compare(
                left=ast.BinOp(left=variable, op=ast.BitAnd(), right=ast.Num(n=0xFF)),
                ops=[op],
                comparators=[ast.BinOp(left=value_ast, op=ast.BitAnd(), right=ast.Num(n=0xFF))]
            ))
            prev_body = node_if_true
            top_if = None
            for i in range(len(if_conditions)-1, -1, -1):
                if_statement = ast.If(
                    test=if_conditions[i],
                    body=prev_body,
                    orelse=[]
                )
                prev_body = [if_statement]
                if i < len(if_conditions)-1:
                    if isinstance(op, ast.Gt) or isinstance(op, ast.Lt):
                        gt_if_cond = copy(if_conditions[i])
                        gt_if_cond.ops = [ast.Gt()]
                        prev_body.append(ast.If(
                        test=gt_if_cond,
                        body=node_if_true,
                        orelse=[]
                        ))
                    elif isinstance(op, ast.Lt):
                        op = ast.Gt()
                        lt_if_cond = copy(if_conditions[i])
                        lt_if_cond.ops = [ast.Lt()]
                        prev_body.append(ast.If(
                            test=lt_if_cond,
                            body=node_if_true,
                            orelse=[]
                        ))
                if i == 0:
                    top_if = prev_body

            sign_comp.body = top_if
            if sign == 0 and isinstance(original_op, ast.Gt):
                sign_comp.orelse = [node_if_true]
            elif sign == 1 and isinstance(original_op, ast.Lt):
                sign_comp.orelse = [node_if_true]
            return sign_comp
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
