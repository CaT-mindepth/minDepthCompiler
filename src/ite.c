
struct Packet {
int field1;
int field2;
};

int state0;

void func(struct Packet p) {
  if (!(!(!(!(p.field1 + p.field2 > 2 + 2))))) {
    state0 = 3 + 4;
  } else {
    state0 = p.field1 - p.field2;
    state0 = state0 + 3 + p.field1;
    state0 = 5;
  }
}

