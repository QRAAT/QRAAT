
def remove_field(l, i):
  return tuple([x[:i] + x[i+1:] for x in l])

def get_field(l, i):
  return tuple([x[i] for x in l])
