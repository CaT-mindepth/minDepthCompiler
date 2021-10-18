#define THRESHOLD 20
#define ARRAY_SIZE 1000000

struct Packet {
  int srcip;
};

int heavy_hitter[ARRAY_SIZE] = {0};
int hh_counter[ARRAY_SIZE] = {0};

void func(struct Packet p) {
  p.srcip = p.srcip;

  if (heavy_hitter[p.srcip] == 0) {
    hh_counter[p.srcip] = hh_counter[p.srcip] + 1;
    if (hh_counter[p.srcip] == THRESHOLD) {
      heavy_hitter[p.srcip] = 1;
    }
  }
}
