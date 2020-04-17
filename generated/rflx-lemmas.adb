package body RFLX.Lemmas with
  SPARK_Mode
is

   procedure Mult_Limit (Value_1 : Big_Integer;
                         Exp_1   : Natural;
                         Value_2 : Big_Integer;
                         Exp_2   : Natural)
   is
   begin
      Mult_Mono (Value_1, To_Big_Integer (2**Exp_1), Value_2);
      pragma Assert (Value_1 * Value_2 <= To_Big_Integer (2**Exp_1) * Value_2);
      Mult_Mono (Value_2, To_Big_Integer (2**Exp_2), To_Big_Integer (2**Exp_1));
      pragma Assert (To_Big_Integer (2**Exp_1) * Value_2 <= To_Big_Integer (2**Exp_1 * 2**Exp_2));
      Exp_Mult (To_Big_Integer (2), Exp_1, Exp_2);
      pragma Assert (2**Exp_1 * 2**Exp_2 = 2**(Exp_1 + Exp_2));
      pragma Assert (Value_1 * Value_2 <= To_Big_Integer (2**(Exp_1 + Exp_2)));
   end Mult_Limit;

   procedure Mult_Ge_0 (Factor_1 : Big_Integer;
                        Factor_2 : Big_Integer)
   is
   begin
      null;
   end Mult_Ge_0;

   procedure Mult_Mono (X : Big_Integer;
                        Y : Big_Integer;
                        Z : Big_Integer)
   is
   begin
      null;
   end Mult_Mono;

   procedure Mult_Div_Id (X : Big_Integer;
                          Y : Big_Integer)
   is
   begin
      null;
   end Mult_Div_Id;

   procedure Div_Pow2_Mono_Strict (X : Big_Integer;
                                   J : Natural;
                                   K : Natural)
   is
   begin
      pragma Assert (J < 63);
      pragma Assert (2**J <= 2**63 - 1);
      --  WORKAROUND: Componolit/Workarounds#15
      pragma Annotate (GNATprove, False_Positive, "assertion",
                       "B > 1 and E1 < E2 => B**E1 < B**E2 => B*E1 <= B**E2 - 1");

      Exp_Div (To_Big_Integer (2), J, K);

      if X / To_Big_Integer (2**K) >= To_Big_Integer (2**J / 2**K) then
         Mult_Mono (To_Big_Integer (2**J / 2**K), X / To_Big_Integer (2**K), To_Big_Integer (2**K));
      end if;

      pragma Assert (2**K * (2**J / 2**K) = 2**K * 2**(J - K));
   end Div_Pow2_Mono_Strict;

   procedure Exp_Mult (Base  : Big_Integer;
                       Exp_1 : Natural;
                       Exp_2 : Natural)
   is
   begin
      null;
   end Exp_Mult;

   procedure Exp_Div (Base  : Big_Integer;
                      Exp_1 : Natural;
                      Exp_2 : Natural)
   is
   begin
      Exp_Mult (Base, Exp_1 - Exp_2, Exp_2);
      Mult_Div_Id (Base**(Exp_1 - Exp_2), Base**Exp_2);
   end Exp_Div;

   procedure Right_Shift_Limit (X : Big_Integer;
                                J : Natural;
                                K : Natural)
   is
   begin
      pragma Assert (J < 63);
      pragma Assert (2**J <= 2**63 - 1);
      --  WORKAROUND: Componolit/Workarounds#15
      pragma Annotate (GNATprove, False_Positive, "assertion",
                       "B > 1 and E1 < E2 => B**E1 < B**E2 => B*E1 <= B**E2 - 1");

      pragma Assert (K < 63);
      pragma Assert (2**K <= 2**63 - 1);
      --  WORKAROUND: Componolit/Workarounds#15
      pragma Annotate (GNATprove, False_Positive, "assertion",
                       "B > 1 and E1 < E2 => B**E1 < B**E2 => B*E1 <= B**E2 - 1");

      Exp_Mult (To_Big_Integer (2), J, K);
      Div_Pow2_Mono_Strict (X, J + K, K);
      Exp_Div (To_Big_Integer (2), J + K, K);
   end Right_Shift_Limit;

   procedure Left_Shift_Limit (X : Big_Integer;
                               J : Natural;
                               K : Natural)
   is
   begin
      Mult_Mono (X + To_Big_Integer (1), To_Big_Integer (2**J), To_Big_Integer (2**K));
      Exp_Mult (To_Big_Integer (2), J, K);
   end Left_Shift_Limit;

end RFLX.Lemmas;
