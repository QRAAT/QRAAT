/** 
 * Peak detection state machine to determine pulse locations
 * State is returned to df_detect
 * Todd Borrowman ECE-UIUC 01/18/08
 */


typedef enum {BELOW_THRESHOLD, ABOVE_THRESHOLD, PEAK, TRIGGER} detect_state_t;

class detectmod_detect;

class peak_detect
{

friend class detectmod_detect; 

private:

  float rise;
  float fall;
  float alpha;
  float peak_value;
  float avg;

  detect_state_t state;

public:

  peak_detect(float rise_in, float fall_in, float alpha_in);
  detect_state_t detect(const float data);
};
