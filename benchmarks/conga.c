struct Packet {
  int util;
  int path_id;
  int src;
  int best_path_util_idx;
  int best_path_idx;
};

int best_path_util[256] = {100};
int best_path[256]      = {-1};

void func(struct Packet p) {
  p.best_path_util_idx = p.best_path_util_idx;
  p.best_path_idx      = p.best_path_idx;
  if (p.util < best_path_util[p.best_path_util_idx]) {
    best_path_util[p.best_path_util_idx] = p.util;
    best_path[p.best_path_idx] = p.path_id;
  } else if (p.path_id == best_path[p.best_path_idx]) {
    best_path_util[p.best_path_util_idx] = p.util;
  }
}
