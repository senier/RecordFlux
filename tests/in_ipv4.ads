with Types; use Types;
with IPv4; use IPv4;
with IPv4.Packet;
with UDP.Datagram;

package In_IPv4
  with SPARK_Mode
is

   function Contains_UDP_In_IPv4 (Buffer : Bytes) return Boolean
     with
       Pre => (IPv4.Packet.Is_Contained (Buffer) and then IPv4.Packet.Is_Valid (Buffer)),
       Post => (if Contains_UDP_In_IPv4'Result then UDP.Datagram.Is_Contained (Buffer (IPv4.Packet.Payload_First (Buffer) .. IPv4.Packet.Payload_Last (Buffer))));

end In_IPv4;