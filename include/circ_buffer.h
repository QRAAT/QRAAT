/**
 * Circ_buffer class implements a circular buffer to store the received signal
 * Todd Borrowman ECE-UIUC 2-21-08
 */

#include <gr_complex.h>

class circ_buffer
{
private:
  int size;
  gr_complex *buffer;
  int index;
  int ch;
  
public:
  circ_buffer(int c, int s);
  circ_buffer(const circ_buffer &cb);
  circ_buffer &operator=(const circ_buffer &cb);
  ~circ_buffer();
  void add(gr_complex *in);
  int get_index();
  gr_complex *get_buffer();
  gr_complex *get_sample();
  void inc_index();

};
