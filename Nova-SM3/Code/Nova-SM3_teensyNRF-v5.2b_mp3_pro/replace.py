import sys

filename = r'c:\Users\sreya\OneDrive\Documents\nova dog\Arduino-Projects\Nova-SM3\Code\Nova-SM3_teensyNRF-v5.2b_mp3_pro\Nova-SM3_teensyNRF-v5.2b_mp3_pro.ino'

with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = """void step_left_right(int lorr, int xdir, int ydir) {
  // TURN-IN-PLACE GAIT (Pure rotation using Coxa servos)
  // Femurs only lift/plant, no forward/backward pushing.
  // Coxas sweep to rotate the body, eliminating drift.

  int s_coxa = 35; // Sweep amplitude for Coxa servos
  
  int c1_RF, c3_RF, c1_LF, c3_LF, c1_RR, c3_RR, c1_LR, c3_LR;

  if (lorr == 1) { // Turn LEFT
    // Push phase (on ground): Front pushes RIGHT, Rear pushes LEFT
    c3_RF = s_coxa;  c3_LF = -s_coxa;
    c3_RR = -s_coxa; c3_LR = s_coxa;
    // Swing phase (in air): Front swings LEFT, Rear swings RIGHT
    c1_RF = -s_coxa; c1_LF = s_coxa;
    c1_RR = s_coxa;  c1_LR = -s_coxa;
  } else {         // Turn RIGHT
    // Push phase (on ground): Front pushes LEFT, Rear pushes RIGHT
    c3_RF = -s_coxa; c3_LF = s_coxa;
    c3_RR = s_coxa;  c3_LR = -s_coxa;
    // Swing phase (in air): Front swings RIGHT, Rear swings LEFT
    c1_RF = s_coxa;  c1_LF = -s_coxa;
    c1_RR = -s_coxa; c1_LR = s_coxa;
  }

  // Femur lift for clearance during swing
  int f_lift_R = -25;
  int f_lift_L = 25;
  
  // Tibia lift for clearance
  int t_lift_R = 40;
  int t_lift_L = -40;

  int csp = 2, fsp = 2, tsp_lift = 1, tsp_drop = 0;  

  bool all_done = (!activeServo[RFC] && !activeServo[RFF] && !activeServo[RFT] &&
                   !activeServo[LFC] && !activeServo[LFF] && !activeServo[LFT] &&
                   !activeServo[RRC] && !activeServo[RRF] && !activeServo[RRT] &&
                   !activeServo[LRC] && !activeServo[LRF] && !activeServo[LRT]);

  if (all_done) {
    if (servoSequence[RF] == 0) {
      // STATE 0: Pair 1 Swings (Phase 0), Pair 2 Pushes (Phase 2)
      // Pair 1 (RF, LR)
      update_sequencer(RF, RFC, (csp*spd_factor), (servoHome[RFC] + c1_RF), 1, 0); 
      update_sequencer(RF, RFF, (fsp*spd_factor), (servoHome[RFF] + f_lift_R), 1, 0);
      update_sequencer(RF, RFT, (tsp_lift*spd_factor), (servoHome[RFT] + t_lift_R), 1, 0);
      update_sequencer(LR, LRC, (csp*spd_factor), (servoHome[LRC] + c1_LR), 1, 0);
      update_sequencer(LR, LRF, (fsp*spd_factor), (servoHome[LRF] + f_lift_L), 1, 0);
      update_sequencer(LR, LRT, (tsp_lift*spd_factor), (servoHome[LRT] + t_lift_L), 1, 0);
      // Pair 2 (LF, RR)
      update_sequencer(LF, LFC, (csp*spd_factor), (servoHome[LFC] + c3_LF), 1, 0);
      update_sequencer(LF, LFF, (fsp*spd_factor), (servoHome[LFF]), 1, 0);
      update_sequencer(LF, LFT, (fsp*spd_factor), (servoHome[LFT]), 1, 0);
      update_sequencer(RR, RRC, (csp*spd_factor), (servoHome[RRC] + c3_RR), 1, 0);
      update_sequencer(RR, RRF, (fsp*spd_factor), (servoHome[RRF]), 1, 0);
      update_sequencer(RR, RRT, (fsp*spd_factor), (servoHome[RRT]), 1, 0);
    }
    else if (servoSequence[RF] == 1) {
      // STATE 1: Pair 1 Plants (Phase 1), Pair 2 Holds (Phase 3)
      // Pair 1
      update_sequencer(RF, RFC, (csp*spd_factor), (servoHome[RFC] + c1_RF), 2, 0); 
      update_sequencer(RF, RFF, (fsp*spd_factor), (servoHome[RFF]), 2, 0);
      update_sequencer(RF, RFT, (tsp_drop*spd_factor), (servoHome[RFT]), 2, 0);
      update_sequencer(LR, LRC, (csp*spd_factor), (servoHome[LRC] + c1_LR), 2, 0);
      update_sequencer(LR, LRF, (fsp*spd_factor), (servoHome[LRF]), 2, 0);
      update_sequencer(LR, LRT, (tsp_drop*spd_factor), (servoHome[LRT]), 2, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*spd_factor), (servoHome[LFC] + c3_LF), 2, 0);
      update_sequencer(LF, LFF, (fsp*spd_factor), (servoHome[LFF]), 2, 0);
      update_sequencer(LF, LFT, (tsp_drop*spd_factor), (servoHome[LFT]), 2, 0);
      update_sequencer(RR, RRC, (csp*spd_factor), (servoHome[RRC] + c3_RR), 2, 0);
      update_sequencer(RR, RRF, (fsp*spd_factor), (servoHome[RRF]), 2, 0);
      update_sequencer(RR, RRT, (tsp_drop*spd_factor), (servoHome[RRT]), 2, 0);
    }
    else if (servoSequence[RF] == 2) {
      // STATE 2: Pair 1 Pushes (Phase 2), Pair 2 Swings (Phase 0)
      // Pair 1
      update_sequencer(RF, RFC, (csp*spd_factor), (servoHome[RFC] + c3_RF), 3, 0); 
      update_sequencer(RF, RFF, (fsp*spd_factor), (servoHome[RFF]), 3, 0);
      update_sequencer(RF, RFT, (fsp*spd_factor), (servoHome[RFT]), 3, 0);
      update_sequencer(LR, LRC, (csp*spd_factor), (servoHome[LRC] + c3_LR), 3, 0);
      update_sequencer(LR, LRF, (fsp*spd_factor), (servoHome[LRF]), 3, 0);
      update_sequencer(LR, LRT, (fsp*spd_factor), (servoHome[LRT]), 3, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*spd_factor), (servoHome[LFC] + c1_LF), 3, 0);
      update_sequencer(LF, LFF, (fsp*spd_factor), (servoHome[LFF] + f_lift_L), 3, 0);
      update_sequencer(LF, LFT, (tsp_lift*spd_factor), (servoHome[LFT] + t_lift_L), 3, 0);
      update_sequencer(RR, RRC, (csp*spd_factor), (servoHome[RRC] + c1_RR), 3, 0);
      update_sequencer(RR, RRF, (fsp*spd_factor), (servoHome[RRF] + f_lift_R), 3, 0);
      update_sequencer(RR, RRT, (tsp_lift*spd_factor), (servoHome[RRT] + t_lift_R), 3, 0);
    }
    else if (servoSequence[RF] == 3) {
      // STATE 3: Pair 1 Holds (Phase 3), Pair 2 Plants (Phase 1)
      // Pair 1
      update_sequencer(RF, RFC, (csp*spd_factor), (servoHome[RFC] + c3_RF), 0, 0); 
      update_sequencer(RF, RFF, (fsp*spd_factor), (servoHome[RFF]), 0, 0);
      update_sequencer(RF, RFT, (tsp_drop*spd_factor), (servoHome[RFT]), 0, 0);
      update_sequencer(LR, LRC, (csp*spd_factor), (servoHome[LRC] + c3_LR), 0, 0);
      update_sequencer(LR, LRF, (fsp*spd_factor), (servoHome[LRF]), 0, 0);
      update_sequencer(LR, LRT, (tsp_drop*spd_factor), (servoHome[LRT]), 0, 0);
      // Pair 2
      update_sequencer(LF, LFC, (csp*spd_factor), (servoHome[LFC] + c1_LF), 0, 0);
      update_sequencer(LF, LFF, (fsp*spd_factor), (servoHome[LFF]), 0, 0);
      update_sequencer(LF, LFT, (tsp_drop*spd_factor), (servoHome[LFT]), 0, 0);
      update_sequencer(RR, RRC, (csp*spd_factor), (servoHome[RRC] + c1_RR), 0, 0);
      update_sequencer(RR, RRF, (fsp*spd_factor), (servoHome[RRF]), 0, 0);
      update_sequencer(RR, RRT, (tsp_drop*spd_factor), (servoHome[RRT]), 0, 0);
      
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

# Replace lines 4611 to 4803 (which are index 4610 to 4802)
# But wait, python arrays are zero-indexed, so line 4611 is index 4610.
# The slice to replace is lines[4610:4803]. Let's verify by checking the text.

if 'void step_left_right' in lines[4610]:
    lines = lines[:4610] + [new_func + '\n'] + lines[4803:]
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Successfully replaced step_left_right')
else:
    print('Error: Line 4611 is not void step_left_right. It is: ' + lines[4610])
