pragma SPARK_Mode;
with RFLX.Scalar_Sequence;
with RFLX.Arrays;

package RFLX.Arrays.Enumeration_Vector is new Scalar_Sequence (Enumeration, Enumeration_Base, Convert, Valid, Convert);