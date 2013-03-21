/**
 * Accumulator class implements a circular buffer with a stored value for the sum of the buffer's contents
 * This is treated as a time-matched filter for use by the detector class
 * Todd Borrowman ECE-UIUC 2-21-08
 */

#include<complex>

class accumulator
{
private:
  int size;
  std::complex<float> *buffer;
  std::complex<double> total_sum;
  int index;

  
public:
  accumulator(int s);
  ~accumulator();
  std::complex<float> add(std::complex<float> in);
  std::complex<float> value();
};
