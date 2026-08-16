import sys

filename = r'c:\Users\sreya\OneDrive\Documents\nova dog\Arduino-Projects\Nova-SM3\Code\Nova-SM3_teensyNRF-v5.2b_mp3_pro\Nova-SM3_teensyNRF-v5.2b_mp3_pro.ino'

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = """void step_left_right(int lorr, int xdir, int ydir) {
  // TRUE TROT TURN-IN-PLACE GAIT
  // Derived from step_forward trot gait, but with left and right legs
  // moving in opposite directions to rotate the chassis.

  int s = 45; // Stride amplitude (increased for faster turning)
  
  // Separate stride arrays for Right and Left legs
  int s1f_R, s2f_R, s3f_R, s4f_R;
  int s1f_L, s2f_L, s3f_L, s4f_L;

  if (lorr == 1) { 
    // lorr == 1 is triggered by 'A' (move_left).
    // User requested flipping the direction, so this will TURN RIGHT.
    // Turn RIGHT: right legs walk backward, left legs walk forward
    s1f_R = s;  s2f_R = s;  s3f_R = -s; s4f_R = -s;  // Right goes Backward
    s1f_L = -s; s2f_L = -s; s3f_L = s;  s4f_L = s;   // Left goes Forward
  } else {         
    // lorr == 0 is triggered by 'D' (move_right).
    // This will TURN LEFT.
    // Turn LEFT: right legs walk forward, left legs walk backward
    s1f_R = -s; s2f_R = -s; s3f_R = s;  s4f_R = s;   // Right goes Forward
    s1f_L = s;  s2f_L = s;  s3f_L = -s; s4f_L = -s;  // Left goes Backward
  }

  int s1t = 45;       // Phase 0: LIFT leg (increased for better clearance during turn)
  int s2t = 0;        // Phase 1: PLANT leg
  int s3t = 0;        // Phase 2: KEEP planted
  int s4t = 0;        // Phase 3: KEEP planted

  int cd = 0; // No coxa sweep during rotation
  
  // Speed up the turning gait
  int turn_spd_factor = spd_factor;
  int csp = 2, fsp = 2, tsp_lift = 2, tsp_drop = 0;  

  bool all_done = (!activeServo[RFC] && !activeServo[RFF] && !activeServo[RFT] &&
                   !activeServo[LFC] && !activeServo[LFF] && !activeServo[LFT] &&
                   !activeServo[RRC] && !activeServo[RRF] && !activeServo[RRT] &&
                   !activeServo[LRC] && !activeServo[LRF] && !activeServo[LRT]);

  if (all_done) {
    if (servoSequence[RF] == 0) {
      // STATE 0: Pair 1 Swings (Phase 0), Pair 2 Pushes (Phase 2)
      // Pair 1
      update_sequencer(RF, RFC, (csp*turn_spd_factor), (servoHome[RFC] + cd), 1, 0); 
      update_sequencer(RF, RFF, (fsp*turn_spd_factor), (servoHome[RFF] + s1f_R), 1, 0);
      update_sequencer(RF, RFT, (tsp_lift*turn_spd_factor), (servoHome[RFT] + s1t), 1, 0);
      update_sequencer(LR, LRC, (csp*turn_spd_factor), (servoHome[LRC] + cd), 1, 0);
      update_sequencer(LR, LRF, (fsp*turn_spd_factor), (servoHome[LRF] - s1f_L), 1, 0);
      update_sequencer(LR, LRT, (tsp_lift*turn_spd_factor), (servoHome[LRT] - s1t), 1, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*turn_spd_factor), (servoHome[LFC] + cd), 1, 0);
      update_sequencer(LF, LFF, (fsp*turn_spd_factor), (servoHome[LFF] - s3f_L), 1, 0);
      update_sequencer(LF, LFT, (fsp*turn_spd_factor), (servoHome[LFT] + s3t), 1, 0);
      update_sequencer(RR, RRC, (csp*turn_spd_factor), (servoHome[RRC] + cd), 1, 0);
      update_sequencer(RR, RRF, (fsp*turn_spd_factor), (servoHome[RRF] + s3f_R), 1, 0);
      update_sequencer(RR, RRT, (fsp*turn_spd_factor), (servoHome[RRT] + s3t), 1, 0);
    }
    else if (servoSequence[RF] == 1) {
      // STATE 1: Pair 1 Plants (Phase 1), Pair 2 Holds (Phase 3)
      // Pair 1
      update_sequencer(RF, RFC, (csp*turn_spd_factor), (servoHome[RFC] + cd), 2, 0); 
      update_sequencer(RF, RFF, (fsp*turn_spd_factor), (servoHome[RFF] + s2f_R), 2, 0);
      update_sequencer(RF, RFT, (tsp_drop*turn_spd_factor), (servoHome[RFT] + s2t), 2, 0);
      update_sequencer(LR, LRC, (csp*turn_spd_factor), (servoHome[LRC] + cd), 2, 0);
      update_sequencer(LR, LRF, (fsp*turn_spd_factor), (servoHome[LRF] - s2f_L), 2, 0);
      update_sequencer(LR, LRT, (tsp_drop*turn_spd_factor), (servoHome[LRT] - s2t), 2, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*turn_spd_factor), (servoHome[LFC] + cd), 2, 0);
      update_sequencer(LF, LFF, (fsp*turn_spd_factor), (servoHome[LFF] - s4f_L), 2, 0);
      update_sequencer(LF, LFT, (tsp_drop*turn_spd_factor), (servoHome[LFT] - s4t), 2, 0);
      update_sequencer(RR, RRC, (csp*turn_spd_factor), (servoHome[RRC] + cd), 2, 0);
      update_sequencer(RR, RRF, (fsp*turn_spd_factor), (servoHome[RRF] + s4f_R), 2, 0);
      update_sequencer(RR, RRT, (tsp_drop*turn_spd_factor), (servoHome[RRT] + s4t), 2, 0);
    }
    else if (servoSequence[RF] == 2) {
      // STATE 2: Pair 1 Pushes (Phase 2), Pair 2 Swings (Phase 0)
      // Pair 1
      update_sequencer(RF, RFC, (csp*turn_spd_factor), (servoHome[RFC] + cd), 3, 0); 
      update_sequencer(RF, RFF, (fsp*turn_spd_factor), (servoHome[RFF] + s3f_R), 3, 0);
      update_sequencer(RF, RFT, (fsp*turn_spd_factor), (servoHome[RFT] + s3t), 3, 0);
      update_sequencer(LR, LRC, (csp*turn_spd_factor), (servoHome[LRC] + cd), 3, 0);
      update_sequencer(LR, LRF, (fsp*turn_spd_factor), (servoHome[LRF] - s3f_L), 3, 0);
      update_sequencer(LR, LRT, (fsp*turn_spd_factor), (servoHome[LRT] - s3t), 3, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*turn_spd_factor), (servoHome[LFC] + cd), 3, 0);
      update_sequencer(LF, LFF, (fsp*turn_spd_factor), (servoHome[LFF] - s1f_L), 3, 0);
      update_sequencer(LF, LFT, (tsp_lift*turn_spd_factor), (servoHome[LFT] - s1t), 3, 0);
      update_sequencer(RR, RRC, (csp*turn_spd_factor), (servoHome[RRC] + cd), 3, 0);
      update_sequencer(RR, RRF, (fsp*turn_spd_factor), (servoHome[RRF] + s1f_R), 3, 0);
      update_sequencer(RR, RRT, (tsp_lift*turn_spd_factor), (servoHome[RRT] + s1t), 3, 0);
    }
    else if (servoSequence[RF] == 3) {
      // STATE 3: Pair 1 Holds (Phase 3), Pair 2 Plants (Phase 1)
      // Pair 1
      update_sequencer(RF, RFC, (csp*turn_spd_factor), (servoHome[RFC] + cd), 0, 0); 
      update_sequencer(RF, RFF, (fsp*turn_spd_factor), (servoHome[RFF] + s4f_R), 0, 0);
      update_sequencer(RF, RFT, (tsp_drop*turn_spd_factor), (servoHome[RFT] + s4t), 0, 0);
      update_sequencer(LR, LRC, (csp*turn_spd_factor), (servoHome[LRC] + cd), 0, 0);
      update_sequencer(LR, LRF, (fsp*turn_spd_factor), (servoHome[LRF] - s4f_L), 0, 0);
      update_sequencer(LR, LRT, (tsp_drop*turn_spd_factor), (servoHome[LRT] - s4t), 0, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*turn_spd_factor), (servoHome[LFC] + cd), 0, 0);
      update_sequencer(LF, LFF, (fsp*turn_spd_factor), (servoHome[LFF] - s2f_L), 0, 0);
      update_sequencer(LF, LFT, (tsp_drop*turn_spd_factor), (servoHome[LFT] - s2t), 0, 0);
      update_sequencer(RR, RRC, (csp*turn_spd_factor), (servoHome[RRC] + cd), 0, 0);
      update_sequencer(RR, RRF, (fsp*turn_spd_factor), (servoHome[RRF] + s2f_R), 0, 0);
      update_sequencer(RR, RRT, (tsp_drop*turn_spd_factor), (servoHome[RRT] + s2t), 0, 0);
      
      lastMoveDelayUpdate = millis();
    }
  }
  if (move_loops) {
    move_loops--;
    if (!move_loops) {
      move_left = 0;
      move_right = 0;
    }
  }
}
"""

# Same exact lines 4610 to 4802.
# Since my previous script replaced lines 4610 to 4802, the length of the file changed!
# Wait! I ran the previous script, and it replaced lines 4610:4803. 
# But the NEW function is SHORTER than the original step_left_right!
# The new function has 84 lines. The original had 193 lines!
# So if I blindly replace lines 4610 to 4803 NOW, I will delete oid wake() and more!
# Good thing I am thinking!

# Find the start and end of step_left_right dynamically!
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.startswith('void step_left_right('):
        start_idx = i
    if start_idx != -1 and line.startswith('void wake()'):
        # wake() is found. The end of step_left_right is a few lines above wake()
        end_idx = i - 4
        break

if start_idx != -1 and end_idx != -1:
    lines = lines[:start_idx] + [new_func + '\n'] + lines[end_idx+1:]
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Successfully replaced step_left_right dynamically!')
else:
    print(f'Error finding bounds. Start: {start_idx}, End: {end_idx}')
