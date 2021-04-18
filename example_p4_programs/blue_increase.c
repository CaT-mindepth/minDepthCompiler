#define FREEZE_TIME 10
#define DELTA1 1
#define DELTA2 2
#define QMAX 5

struct Packet {
  int loss;
  int qlen;
  int now;
  int link_idle;
  int cond1;
  int now_plus_free;
};

int last_update;
int p_mark;

void func(struct Packet p) {
  p.now_plus_free = p.now - FREEZE_TIME;
// Run when q exceeds QMAX or on packet loss (higher priority?)
  if (p.now_plus_free > last_update) {
     p_mark = p_mark + DELTA1;
     last_update = p.now;
  }
}
