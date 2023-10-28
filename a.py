import ast

from bug import entrypoint
from bug import get_initial_corpus

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
        if self.check_integer_comparison(condition):
            #Todo: Have bugs when multi-conditions
            #node = self.transformGEQLEQ(node)
            node = self.split_compares_pass(node)
        elif self.check_string_comparison(condition):
            node = self.compare_transform_pass(node)
        return node


    """
        We assume string comparison has two operands and one operator
    """
    def check_string_comparison(self, condition):
        if isinstance(condition, ast.Compare):
            left = condition.left
            if isinstance(left, ast.Str):
                if isinstance(condition.comparators[0], ast.Name):
                    return True
            elif isinstance(left, ast.Name):
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
                if isinstance(condition.comparators[0], ast.Name):
                    return True
            elif isinstance(left, ast.Name):
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
                #this array disjuncts the < and == condition
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
            node.test = ast.copy_location(new_node, node.test)
            return node
        return node

    def compare_transform_pass(self, node):
        condition = node.test
        if isinstance(condition, ast.Compare):
            op = condition.ops[0]
            left = condition.left
            right = condition.comparators[0]
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
                len_GT_check = ast.Compare(left=len_call, ops=[ast.Gt()], comparators=[ast.Num(n=i)])
                var_idx = ast.Subscript(
                    value=variable,
                    slice=ast.Index(value=ast.Num(n=i)),
                    ctx=ast.Load()
                )
                char_check = ast.Compare(left=var_idx, ops=[op], comparators=[ast.Str(value=str_value[i])])
                if_conditions.append(ast.BoolOp(op=ast.And(), values=[len_GT_check, char_check]))
            len_check = ast.Compare(left=len_call, ops=[ast.LtE()], comparators=[ast.Num(n=len(str_value))])
            len_check_statement = ast.If(
                test=len_check,
                body=node.body,
                orelse=node.orelse
            )
            prev_body = [len_check_statement]
            prev_or_else = []
            for i in range(len(str_value)-1, -1, -1):
                if_statement = ast.If(
                    test=if_conditions[i],
                    body=prev_body,
                    orelse=prev_or_else
                )
                prev_or_else = []
                prev_body = [if_statement]
                if i == 0:
                    node = if_statement
            return node
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
                            left=ast.BinOp(left=ast.BinOp(left=condition.left, op=ast.BitAnd(), right=ast.Num(n=0xFF0000)),
                                           op=ast.RShift(), right=ast.Num(n=16)),
                            ops=[op],
                            comparators=[ast.BinOp(left=ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF0000))
                                                   , op=ast.RShift(), right=ast.Num(n=16))]
                        ))
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(left=ast.BinOp(left=condition.left, op=ast.BitAnd(), right=ast.Num(n=0xFF00))
                                           , op=ast.RShift(), right=ast.Num(n=8)),
                            ops=[op],
                            comparators=[ast.BinOp(left=ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF00))
                                                   , op=ast.RShift(), right=ast.Num(n=8))]
                        ))
                        if_conditions.append(ast.Compare(
                            left=ast.BinOp(left=condition.left, op=ast.RShift(), right=ast.Num(n=0xFF)),
                            ops=[op],
                            comparators=[ast.BinOp(left=comparator, op=ast.BitAnd(), right=ast.Num(n=0xFF))]
                        ))
                        prev_body = node.body
                        prev_or_else = node.orelse
                        for i in range(3,-1,-1):
                            if_statement = ast.If(
                                test=if_conditions[i],
                                body=prev_body,
                                orelse=prev_or_else
                            )
                            prev_or_else = []
                            prev_body = [if_statement]
                            if i == 0:
                                node = if_statement
                        return node
        return node


f = open('bug.py','r')
content = f.read()
parsed_ast = ast.parse(content)
finder = FunctionFinder()
transformer = LafIntelTransformer()
finder.visit(parsed_ast)
function_node = finder.function_node

modified_code = ast.unparse(transformer.visit(function_node))
print(modified_code)