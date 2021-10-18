struct Packet {
  int a;
  int b;
  int cond;
};

void func(struct Packet p) {
  if (p.cond > 0) {
    p.a = p.b + 3;
    p.a = p.a + p.cond + 6;
  } else {
    p.a = p.b + 3;
    p.a = p.a + p.cond - 4;
  }
}

