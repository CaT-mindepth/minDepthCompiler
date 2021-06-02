# Generated from alu.g4 by ANTLR 4.9.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .aluParser import aluParser
else:
    from aluParser import aluParser

# This class defines a complete listener for a parse tree produced by aluParser.
class aluListener(ParseTreeListener):

    # Enter a parse tree produced by aluParser#state_var.
    def enterState_var(self, ctx:aluParser.State_varContext):
        pass

    # Exit a parse tree produced by aluParser#state_var.
    def exitState_var(self, ctx:aluParser.State_varContext):
        pass


    # Enter a parse tree produced by aluParser#temp_var.
    def enterTemp_var(self, ctx:aluParser.Temp_varContext):
        pass

    # Exit a parse tree produced by aluParser#temp_var.
    def exitTemp_var(self, ctx:aluParser.Temp_varContext):
        pass


    # Enter a parse tree produced by aluParser#packet_field.
    def enterPacket_field(self, ctx:aluParser.Packet_fieldContext):
        pass

    # Exit a parse tree produced by aluParser#packet_field.
    def exitPacket_field(self, ctx:aluParser.Packet_fieldContext):
        pass


    # Enter a parse tree produced by aluParser#hole_var.
    def enterHole_var(self, ctx:aluParser.Hole_varContext):
        pass

    # Exit a parse tree produced by aluParser#hole_var.
    def exitHole_var(self, ctx:aluParser.Hole_varContext):
        pass


    # Enter a parse tree produced by aluParser#stateless.
    def enterStateless(self, ctx:aluParser.StatelessContext):
        pass

    # Exit a parse tree produced by aluParser#stateless.
    def exitStateless(self, ctx:aluParser.StatelessContext):
        pass


    # Enter a parse tree produced by aluParser#stateful.
    def enterStateful(self, ctx:aluParser.StatefulContext):
        pass

    # Exit a parse tree produced by aluParser#stateful.
    def exitStateful(self, ctx:aluParser.StatefulContext):
        pass


    # Enter a parse tree produced by aluParser#state_indicator.
    def enterState_indicator(self, ctx:aluParser.State_indicatorContext):
        pass

    # Exit a parse tree produced by aluParser#state_indicator.
    def exitState_indicator(self, ctx:aluParser.State_indicatorContext):
        pass


    # Enter a parse tree produced by aluParser#state_var_def.
    def enterState_var_def(self, ctx:aluParser.State_var_defContext):
        pass

    # Exit a parse tree produced by aluParser#state_var_def.
    def exitState_var_def(self, ctx:aluParser.State_var_defContext):
        pass


    # Enter a parse tree produced by aluParser#state_var_seq.
    def enterState_var_seq(self, ctx:aluParser.State_var_seqContext):
        pass

    # Exit a parse tree produced by aluParser#state_var_seq.
    def exitState_var_seq(self, ctx:aluParser.State_var_seqContext):
        pass


    # Enter a parse tree produced by aluParser#SingleStateVar.
    def enterSingleStateVar(self, ctx:aluParser.SingleStateVarContext):
        pass

    # Exit a parse tree produced by aluParser#SingleStateVar.
    def exitSingleStateVar(self, ctx:aluParser.SingleStateVarContext):
        pass


    # Enter a parse tree produced by aluParser#MultipleStateVars.
    def enterMultipleStateVars(self, ctx:aluParser.MultipleStateVarsContext):
        pass

    # Exit a parse tree produced by aluParser#MultipleStateVars.
    def exitMultipleStateVars(self, ctx:aluParser.MultipleStateVarsContext):
        pass


    # Enter a parse tree produced by aluParser#hole_def.
    def enterHole_def(self, ctx:aluParser.Hole_defContext):
        pass

    # Exit a parse tree produced by aluParser#hole_def.
    def exitHole_def(self, ctx:aluParser.Hole_defContext):
        pass


    # Enter a parse tree produced by aluParser#hole_seq.
    def enterHole_seq(self, ctx:aluParser.Hole_seqContext):
        pass

    # Exit a parse tree produced by aluParser#hole_seq.
    def exitHole_seq(self, ctx:aluParser.Hole_seqContext):
        pass


    # Enter a parse tree produced by aluParser#SingleHoleVar.
    def enterSingleHoleVar(self, ctx:aluParser.SingleHoleVarContext):
        pass

    # Exit a parse tree produced by aluParser#SingleHoleVar.
    def exitSingleHoleVar(self, ctx:aluParser.SingleHoleVarContext):
        pass


    # Enter a parse tree produced by aluParser#MultipleHoleVars.
    def enterMultipleHoleVars(self, ctx:aluParser.MultipleHoleVarsContext):
        pass

    # Exit a parse tree produced by aluParser#MultipleHoleVars.
    def exitMultipleHoleVars(self, ctx:aluParser.MultipleHoleVarsContext):
        pass


    # Enter a parse tree produced by aluParser#packet_field_def.
    def enterPacket_field_def(self, ctx:aluParser.Packet_field_defContext):
        pass

    # Exit a parse tree produced by aluParser#packet_field_def.
    def exitPacket_field_def(self, ctx:aluParser.Packet_field_defContext):
        pass


    # Enter a parse tree produced by aluParser#packet_field_seq.
    def enterPacket_field_seq(self, ctx:aluParser.Packet_field_seqContext):
        pass

    # Exit a parse tree produced by aluParser#packet_field_seq.
    def exitPacket_field_seq(self, ctx:aluParser.Packet_field_seqContext):
        pass


    # Enter a parse tree produced by aluParser#SinglePacketField.
    def enterSinglePacketField(self, ctx:aluParser.SinglePacketFieldContext):
        pass

    # Exit a parse tree produced by aluParser#SinglePacketField.
    def exitSinglePacketField(self, ctx:aluParser.SinglePacketFieldContext):
        pass


    # Enter a parse tree produced by aluParser#MultiplePacketFields.
    def enterMultiplePacketFields(self, ctx:aluParser.MultiplePacketFieldsContext):
        pass

    # Exit a parse tree produced by aluParser#MultiplePacketFields.
    def exitMultiplePacketFields(self, ctx:aluParser.MultiplePacketFieldsContext):
        pass


    # Enter a parse tree produced by aluParser#alu_body.
    def enterAlu_body(self, ctx:aluParser.Alu_bodyContext):
        pass

    # Exit a parse tree produced by aluParser#alu_body.
    def exitAlu_body(self, ctx:aluParser.Alu_bodyContext):
        pass


    # Enter a parse tree produced by aluParser#condition_block.
    def enterCondition_block(self, ctx:aluParser.Condition_blockContext):
        pass

    # Exit a parse tree produced by aluParser#condition_block.
    def exitCondition_block(self, ctx:aluParser.Condition_blockContext):
        pass


    # Enter a parse tree produced by aluParser#StmtUpdateExpr.
    def enterStmtUpdateExpr(self, ctx:aluParser.StmtUpdateExprContext):
        pass

    # Exit a parse tree produced by aluParser#StmtUpdateExpr.
    def exitStmtUpdateExpr(self, ctx:aluParser.StmtUpdateExprContext):
        pass


    # Enter a parse tree produced by aluParser#StmtUpdateTempInt.
    def enterStmtUpdateTempInt(self, ctx:aluParser.StmtUpdateTempIntContext):
        pass

    # Exit a parse tree produced by aluParser#StmtUpdateTempInt.
    def exitStmtUpdateTempInt(self, ctx:aluParser.StmtUpdateTempIntContext):
        pass


    # Enter a parse tree produced by aluParser#StmtUpdateTempBit.
    def enterStmtUpdateTempBit(self, ctx:aluParser.StmtUpdateTempBitContext):
        pass

    # Exit a parse tree produced by aluParser#StmtUpdateTempBit.
    def exitStmtUpdateTempBit(self, ctx:aluParser.StmtUpdateTempBitContext):
        pass


    # Enter a parse tree produced by aluParser#StmtReturn.
    def enterStmtReturn(self, ctx:aluParser.StmtReturnContext):
        pass

    # Exit a parse tree produced by aluParser#StmtReturn.
    def exitStmtReturn(self, ctx:aluParser.StmtReturnContext):
        pass


    # Enter a parse tree produced by aluParser#StmtIfElseIfElse.
    def enterStmtIfElseIfElse(self, ctx:aluParser.StmtIfElseIfElseContext):
        pass

    # Exit a parse tree produced by aluParser#StmtIfElseIfElse.
    def exitStmtIfElseIfElse(self, ctx:aluParser.StmtIfElseIfElseContext):
        pass


    # Enter a parse tree produced by aluParser#AssertFalse.
    def enterAssertFalse(self, ctx:aluParser.AssertFalseContext):
        pass

    # Exit a parse tree produced by aluParser#AssertFalse.
    def exitAssertFalse(self, ctx:aluParser.AssertFalseContext):
        pass


    # Enter a parse tree produced by aluParser#return_statement.
    def enterReturn_statement(self, ctx:aluParser.Return_statementContext):
        pass

    # Exit a parse tree produced by aluParser#return_statement.
    def exitReturn_statement(self, ctx:aluParser.Return_statementContext):
        pass


    # Enter a parse tree produced by aluParser#variable.
    def enterVariable(self, ctx:aluParser.VariableContext):
        pass

    # Exit a parse tree produced by aluParser#variable.
    def exitVariable(self, ctx:aluParser.VariableContext):
        pass


    # Enter a parse tree produced by aluParser#Or.
    def enterOr(self, ctx:aluParser.OrContext):
        pass

    # Exit a parse tree produced by aluParser#Or.
    def exitOr(self, ctx:aluParser.OrContext):
        pass


    # Enter a parse tree produced by aluParser#Var.
    def enterVar(self, ctx:aluParser.VarContext):
        pass

    # Exit a parse tree produced by aluParser#Var.
    def exitVar(self, ctx:aluParser.VarContext):
        pass


    # Enter a parse tree produced by aluParser#Constant.
    def enterConstant(self, ctx:aluParser.ConstantContext):
        pass

    # Exit a parse tree produced by aluParser#Constant.
    def exitConstant(self, ctx:aluParser.ConstantContext):
        pass


    # Enter a parse tree produced by aluParser#True.
    def enterTrue(self, ctx:aluParser.TrueContext):
        pass

    # Exit a parse tree produced by aluParser#True.
    def exitTrue(self, ctx:aluParser.TrueContext):
        pass


    # Enter a parse tree produced by aluParser#RelOp.
    def enterRelOp(self, ctx:aluParser.RelOpContext):
        pass

    # Exit a parse tree produced by aluParser#RelOp.
    def exitRelOp(self, ctx:aluParser.RelOpContext):
        pass


    # Enter a parse tree produced by aluParser#GreaterEqual.
    def enterGreaterEqual(self, ctx:aluParser.GreaterEqualContext):
        pass

    # Exit a parse tree produced by aluParser#GreaterEqual.
    def exitGreaterEqual(self, ctx:aluParser.GreaterEqualContext):
        pass


    # Enter a parse tree produced by aluParser#Opt.
    def enterOpt(self, ctx:aluParser.OptContext):
        pass

    # Exit a parse tree produced by aluParser#Opt.
    def exitOpt(self, ctx:aluParser.OptContext):
        pass


    # Enter a parse tree produced by aluParser#Mux3WithNum.
    def enterMux3WithNum(self, ctx:aluParser.Mux3WithNumContext):
        pass

    # Exit a parse tree produced by aluParser#Mux3WithNum.
    def exitMux3WithNum(self, ctx:aluParser.Mux3WithNumContext):
        pass


    # Enter a parse tree produced by aluParser#ArithOp.
    def enterArithOp(self, ctx:aluParser.ArithOpContext):
        pass

    # Exit a parse tree produced by aluParser#ArithOp.
    def exitArithOp(self, ctx:aluParser.ArithOpContext):
        pass


    # Enter a parse tree produced by aluParser#ExprWithParen.
    def enterExprWithParen(self, ctx:aluParser.ExprWithParenContext):
        pass

    # Exit a parse tree produced by aluParser#ExprWithParen.
    def exitExprWithParen(self, ctx:aluParser.ExprWithParenContext):
        pass


    # Enter a parse tree produced by aluParser#Less.
    def enterLess(self, ctx:aluParser.LessContext):
        pass

    # Exit a parse tree produced by aluParser#Less.
    def exitLess(self, ctx:aluParser.LessContext):
        pass


    # Enter a parse tree produced by aluParser#Mux4.
    def enterMux4(self, ctx:aluParser.Mux4Context):
        pass

    # Exit a parse tree produced by aluParser#Mux4.
    def exitMux4(self, ctx:aluParser.Mux4Context):
        pass


    # Enter a parse tree produced by aluParser#Mux5.
    def enterMux5(self, ctx:aluParser.Mux5Context):
        pass

    # Exit a parse tree produced by aluParser#Mux5.
    def exitMux5(self, ctx:aluParser.Mux5Context):
        pass


    # Enter a parse tree produced by aluParser#ExprWithOp.
    def enterExprWithOp(self, ctx:aluParser.ExprWithOpContext):
        pass

    # Exit a parse tree produced by aluParser#ExprWithOp.
    def exitExprWithOp(self, ctx:aluParser.ExprWithOpContext):
        pass


    # Enter a parse tree produced by aluParser#NotEqual.
    def enterNotEqual(self, ctx:aluParser.NotEqualContext):
        pass

    # Exit a parse tree produced by aluParser#NotEqual.
    def exitNotEqual(self, ctx:aluParser.NotEqualContext):
        pass


    # Enter a parse tree produced by aluParser#ComputeAlu.
    def enterComputeAlu(self, ctx:aluParser.ComputeAluContext):
        pass

    # Exit a parse tree produced by aluParser#ComputeAlu.
    def exitComputeAlu(self, ctx:aluParser.ComputeAluContext):
        pass


    # Enter a parse tree produced by aluParser#Ternary.
    def enterTernary(self, ctx:aluParser.TernaryContext):
        pass

    # Exit a parse tree produced by aluParser#Ternary.
    def exitTernary(self, ctx:aluParser.TernaryContext):
        pass


    # Enter a parse tree produced by aluParser#Mux2.
    def enterMux2(self, ctx:aluParser.Mux2Context):
        pass

    # Exit a parse tree produced by aluParser#Mux2.
    def exitMux2(self, ctx:aluParser.Mux2Context):
        pass


    # Enter a parse tree produced by aluParser#Num.
    def enterNum(self, ctx:aluParser.NumContext):
        pass

    # Exit a parse tree produced by aluParser#Num.
    def exitNum(self, ctx:aluParser.NumContext):
        pass


    # Enter a parse tree produced by aluParser#Mux3.
    def enterMux3(self, ctx:aluParser.Mux3Context):
        pass

    # Exit a parse tree produced by aluParser#Mux3.
    def exitMux3(self, ctx:aluParser.Mux3Context):
        pass


    # Enter a parse tree produced by aluParser#LessEqual.
    def enterLessEqual(self, ctx:aluParser.LessEqualContext):
        pass

    # Exit a parse tree produced by aluParser#LessEqual.
    def exitLessEqual(self, ctx:aluParser.LessEqualContext):
        pass


    # Enter a parse tree produced by aluParser#NOT.
    def enterNOT(self, ctx:aluParser.NOTContext):
        pass

    # Exit a parse tree produced by aluParser#NOT.
    def exitNOT(self, ctx:aluParser.NOTContext):
        pass


    # Enter a parse tree produced by aluParser#Equals.
    def enterEquals(self, ctx:aluParser.EqualsContext):
        pass

    # Exit a parse tree produced by aluParser#Equals.
    def exitEquals(self, ctx:aluParser.EqualsContext):
        pass


    # Enter a parse tree produced by aluParser#And.
    def enterAnd(self, ctx:aluParser.AndContext):
        pass

    # Exit a parse tree produced by aluParser#And.
    def exitAnd(self, ctx:aluParser.AndContext):
        pass


    # Enter a parse tree produced by aluParser#Greater.
    def enterGreater(self, ctx:aluParser.GreaterContext):
        pass

    # Exit a parse tree produced by aluParser#Greater.
    def exitGreater(self, ctx:aluParser.GreaterContext):
        pass


    # Enter a parse tree produced by aluParser#BoolOp.
    def enterBoolOp(self, ctx:aluParser.BoolOpContext):
        pass

    # Exit a parse tree produced by aluParser#BoolOp.
    def exitBoolOp(self, ctx:aluParser.BoolOpContext):
        pass


    # Enter a parse tree produced by aluParser#alu.
    def enterAlu(self, ctx:aluParser.AluContext):
        pass

    # Exit a parse tree produced by aluParser#alu.
    def exitAlu(self, ctx:aluParser.AluContext):
        pass



del aluParser