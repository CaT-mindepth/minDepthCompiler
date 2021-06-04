# Generated from alu.g4 by ANTLR 4.9.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .aluParser import aluParser
else:
    from aluParser import aluParser

# This class defines a complete generic visitor for a parse tree produced by aluParser.

class aluVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by aluParser#state_var.
    def visitState_var(self, ctx:aluParser.State_varContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#temp_var.
    def visitTemp_var(self, ctx:aluParser.Temp_varContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#packet_field.
    def visitPacket_field(self, ctx:aluParser.Packet_fieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#hole_var.
    def visitHole_var(self, ctx:aluParser.Hole_varContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#stateless.
    def visitStateless(self, ctx:aluParser.StatelessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#stateful.
    def visitStateful(self, ctx:aluParser.StatefulContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#state_indicator.
    def visitState_indicator(self, ctx:aluParser.State_indicatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#state_var_def.
    def visitState_var_def(self, ctx:aluParser.State_var_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#state_var_seq.
    def visitState_var_seq(self, ctx:aluParser.State_var_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#SingleStateVar.
    def visitSingleStateVar(self, ctx:aluParser.SingleStateVarContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#MultipleStateVars.
    def visitMultipleStateVars(self, ctx:aluParser.MultipleStateVarsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#hole_def.
    def visitHole_def(self, ctx:aluParser.Hole_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#hole_seq.
    def visitHole_seq(self, ctx:aluParser.Hole_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#SingleHoleVar.
    def visitSingleHoleVar(self, ctx:aluParser.SingleHoleVarContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#MultipleHoleVars.
    def visitMultipleHoleVars(self, ctx:aluParser.MultipleHoleVarsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#packet_field_def.
    def visitPacket_field_def(self, ctx:aluParser.Packet_field_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#packet_field_seq.
    def visitPacket_field_seq(self, ctx:aluParser.Packet_field_seqContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#SinglePacketField.
    def visitSinglePacketField(self, ctx:aluParser.SinglePacketFieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#MultiplePacketFields.
    def visitMultiplePacketFields(self, ctx:aluParser.MultiplePacketFieldsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#alu_body.
    def visitAlu_body(self, ctx:aluParser.Alu_bodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#condition_block.
    def visitCondition_block(self, ctx:aluParser.Condition_blockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#StmtUpdateExpr.
    def visitStmtUpdateExpr(self, ctx:aluParser.StmtUpdateExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#StmtUpdateTempInt.
    def visitStmtUpdateTempInt(self, ctx:aluParser.StmtUpdateTempIntContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#StmtUpdateTempBit.
    def visitStmtUpdateTempBit(self, ctx:aluParser.StmtUpdateTempBitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#StmtReturn.
    def visitStmtReturn(self, ctx:aluParser.StmtReturnContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#StmtIfElseIfElse.
    def visitStmtIfElseIfElse(self, ctx:aluParser.StmtIfElseIfElseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#AssertFalse.
    def visitAssertFalse(self, ctx:aluParser.AssertFalseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#return_statement.
    def visitReturn_statement(self, ctx:aluParser.Return_statementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#variable.
    def visitVariable(self, ctx:aluParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Or.
    def visitOr(self, ctx:aluParser.OrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Var.
    def visitVar(self, ctx:aluParser.VarContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Constant.
    def visitConstant(self, ctx:aluParser.ConstantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#True.
    def visitTrue(self, ctx:aluParser.TrueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#RelOp.
    def visitRelOp(self, ctx:aluParser.RelOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#GreaterEqual.
    def visitGreaterEqual(self, ctx:aluParser.GreaterEqualContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Opt.
    def visitOpt(self, ctx:aluParser.OptContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Mux3WithNum.
    def visitMux3WithNum(self, ctx:aluParser.Mux3WithNumContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#ArithOp.
    def visitArithOp(self, ctx:aluParser.ArithOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#ExprWithParen.
    def visitExprWithParen(self, ctx:aluParser.ExprWithParenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Less.
    def visitLess(self, ctx:aluParser.LessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Mux4.
    def visitMux4(self, ctx:aluParser.Mux4Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Mux5.
    def visitMux5(self, ctx:aluParser.Mux5Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#ExprWithOp.
    def visitExprWithOp(self, ctx:aluParser.ExprWithOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#NotEqual.
    def visitNotEqual(self, ctx:aluParser.NotEqualContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#ComputeAlu.
    def visitComputeAlu(self, ctx:aluParser.ComputeAluContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Ternary.
    def visitTernary(self, ctx:aluParser.TernaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Mux2.
    def visitMux2(self, ctx:aluParser.Mux2Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Num.
    def visitNum(self, ctx:aluParser.NumContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Mux3.
    def visitMux3(self, ctx:aluParser.Mux3Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#LessEqual.
    def visitLessEqual(self, ctx:aluParser.LessEqualContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#NOT.
    def visitNOT(self, ctx:aluParser.NOTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Equals.
    def visitEquals(self, ctx:aluParser.EqualsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#And.
    def visitAnd(self, ctx:aluParser.AndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#Greater.
    def visitGreater(self, ctx:aluParser.GreaterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#BoolOp.
    def visitBoolOp(self, ctx:aluParser.BoolOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by aluParser#alu.
    def visitAlu(self, ctx:aluParser.AluContext):
        return self.visitChildren(ctx)



del aluParser