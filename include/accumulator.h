/**
 * Accumulator class implements a circular buffer with a stored value for the sum of the buffer's contents
 * This is treated as a time-matched filter for use by the detector class
 * Todd Borrowman ECE-UIUC 2-21-08
 */

class accumulator
{
private:
  int size;
  float *buffer;
  double total_sum;
  int index;

  
public:
  accumulator(int s);
  ~accumulator();
  float add(float in);
  float value();
};
