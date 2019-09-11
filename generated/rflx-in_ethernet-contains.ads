with RFLX.Ethernet;
use RFLX.Ethernet;
with RFLX.Ethernet.Frame;
with RFLX.IPv4.Packet;

package RFLX.In_Ethernet.Contains with
  SPARK_Mode
is

   function IPv4_Packet_In_Ethernet_Frame_Payload (Context : Ethernet.Frame.Context_Type) return Boolean is
     (Ethernet.Frame.Has_Buffer (Context)
      and then Ethernet.Frame.Present (Context, Ethernet.Frame.F_Payload)
      and then Ethernet.Frame.Valid (Context, Ethernet.Frame.F_Type_Length)
      and then Ethernet.Frame.Get_Type_Length (Context) = 2048);

   procedure Switch (Ethernet_Frame_Context : in out Ethernet.Frame.Context_Type; IPv4_Packet_Context : out IPv4.Packet.Context_Type) with
     Pre =>
       not Ethernet_Frame_Context'Constrained
          and then not IPv4_Packet_Context'Constrained
          and then Ethernet.Frame.Has_Buffer (Ethernet_Frame_Context)
          and then Ethernet.Frame.Present (Ethernet_Frame_Context, Ethernet.Frame.F_Payload)
          and then Ethernet.Frame.Valid (Ethernet_Frame_Context, Ethernet.Frame.F_Type_Length)
          and then IPv4_Packet_In_Ethernet_Frame_Payload (Ethernet_Frame_Context);

end RFLX.In_Ethernet.Contains;