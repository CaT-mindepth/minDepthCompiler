// Sample every 30th packet in a flow
#define N 30

struct Packet {
  int sample;
};

int count = 0;

void func(struct Packet p) {
  if (count == N - 1) {
    p.sample = 1;
    count = 0;
  } else {
    p.sample = 0;
    count = count + 1;
  }
}
