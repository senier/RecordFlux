pragma SPARK_Mode;
with RFLX.Scalar_Sequence;
with RFLX.Arrays;

package RFLX.Arrays.AV_Enumeration_Vector is new Scalar_Sequence (AV_Enumeration, AV_Enumeration_Base, Convert, Valid, Convert);