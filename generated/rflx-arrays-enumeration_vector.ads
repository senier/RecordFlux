pragma Style_Checks ("N3aAbcdefhiIklnOprStux");
pragma SPARK_Mode;
with RFLX.RFLX_Scalar_Sequence;
with RFLX.Arrays;
with RFLX.RFLX_Types;

package RFLX.Arrays.Enumeration_Vector is new RFLX.RFLX_Scalar_Sequence (RFLX.RFLX_Types, Enumeration, Enumeration_Base, Valid, To_Actual, To_Base);
