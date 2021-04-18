#define MAX_ALLOWABLE_RTT 30

struct Packet {
  int size_bytes;
  int rtt;
};
// Total number of bytes seen so far.
int input_traffic_Bytes = 0;

// Sum of rtt so far
int sum_rtt_Tr = 0;

// Number of packets with a valid RTT
int num_pkts_with_rtt = 0;

void func(struct Packet p) {
  input_traffic_Bytes = input_traffic_Bytes + p.size_bytes;
  if (p.rtt < MAX_ALLOWABLE_RTT) {
    sum_rtt_Tr = sum_rtt_Tr + p.rtt;
    num_pkts_with_rtt = num_pkts_with_rtt + 1;
  }
}
