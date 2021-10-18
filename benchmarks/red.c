

struct Packet {
  int q_inst;
  int mark; 
  int prob;
  int gain;
};

int q_avg = 0;

void func(struct Packet p) {
  q_avg = (p.gain * q_avg) + (1 - p.gain) * p.q_inst;
  if (q_avg < 50) {
    p.mark = 0;
  } else if (q_avg > 100) {
    p.mark = 1;
  } else {
    p.prob = (q_avg - 50) * 100000 / (100 - 50);
    p.mark = p.prob;
  }
}
