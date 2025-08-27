# Gaze Tracking User Testing Guide

## Overview

This comprehensive guide explains how the integrated gaze tracking system works with your EDF Viewer software and provides detailed testing procedures to validate functionality in your specific environment.

## How It Works With Your Software

### System Architecture Integration

Your EDF Viewer now includes a complete gaze tracking subsystem that operates alongside existing functionality without disrupting normal workflows:

```
Original EDF Viewer Features          New Gaze Tracking Features
├── EDF File Loading                  ├── Eye Tracker Interface
├── Signal Visualization              ├── Real-time Gaze Processing  
├── Channel Management                ├── Intelligent Annotations
├── Manual Annotations                ├── Enhanced Auto-Scroll
├── Screenshot Tools                  ├── Visual Gaze Feedback
├── Session Management                ├── Behavioral Analytics
└── Keyboard Shortcuts                └── Gaze-Aware Controls
```

### Workflow Integration

#### 1. Normal Viewing Mode (Unchanged)
- All existing functionality works exactly as before
- No performance impact when gaze tracking is disabled
- Familiar interface and controls remain identical

#### 2. Enhanced Gaze Mode
- **Activation**: `Gaze → Setup Gaze Tracking` from menu
- **Visual Feedback**: Real-time gaze cursor on screen
- **Smart Annotations**: Automatic annotations at interesting fixations
- **Adaptive Scrolling**: Auto-scroll pauses at regions of interest
- **Analytics**: Session analytics available via `Gaze → View Analytics`

### Data Flow Integration

1. **EDF Data Loading**: Works exactly as before
2. **Gaze Data Acquisition**: Eye tracker provides real-time gaze coordinates
3. **Coordinate Mapping**: Gaze coordinates mapped to EDF plot space (channels/time)
4. **Context Analysis**: EEG data around fixation analyzed for clinical significance
5. **Intelligent Actions**: Based on analysis, system can:
   - Create automatic annotations
   - Pause auto-scroll for detailed review
   - Provide visual/audio feedback
   - Track user behavior patterns

## Testing Procedures

### Phase 1: Basic Integration Testing

#### Test 1.1: Installation Verification
```bash
# Run from your Edf_viewer directory
python test_integration.py
```
**Expected Result**: All 6 tests should pass
**Success Criteria**: 
- ✅ Component Imports: PASSED
- ✅ Basic Functionality: PASSED  
- ✅ Mock Integration: PASSED
- ✅ Performance: PASSED
- ✅ Error Handling: PASSED
- ✅ Configuration Options: PASSED

#### Test 1.2: Quick Setup Validation
```bash
# Automated integration with main application
python quick_setup.py
```
**Expected Result**: "🎉 SETUP COMPLETE!" message
**Success Criteria**:
- Main EDF viewer patched successfully
- Integration test passes
- No missing dependencies

#### Test 1.3: Application Launch Test
```bash
# Launch your enhanced EDF viewer
python src/main.py
```
**Expected Result**: Application launches normally with new "Gaze" menu
**Success Criteria**:
- Application starts without errors
- New "Gaze" menu appears in menu bar
- All existing functionality still works
- No performance degradation

### Phase 2: Core Functionality Testing

#### Test 2.1: Gaze Menu Availability
1. Launch EDF Viewer
2. Check menu bar for "Gaze" menu
3. Verify menu items:
   - ✅ "Setup Gaze Tracking" (Ctrl+G)
   - ✅ "Toggle Gaze Mode" (initially disabled)
   - ✅ "Enhanced Auto-Scroll" (initially disabled)  
   - ✅ "View Analytics"

#### Test 2.2: Mock Gaze Setup
1. Go to `Gaze → Setup Gaze Tracking`
2. In setup dialog, select "Mock Eye Tracker"
3. Configure settings:
   - Sampling Rate: 60 Hz
   - Min Fixation Duration: 300ms
   - Auto-create annotations: Yes
4. Click "OK"
**Expected**: Success message, gaze options become enabled

#### Test 2.3: Gaze Mode Activation
1. Load an EDF file (any existing EDF file you normally use)
2. Go to `Gaze → Toggle Gaze Mode` (Ctrl+Shift+G)
3. Observe:
   - Status bar shows "Gaze tracking started"
   - No visible gaze cursor (mock tracker doesn't show cursor)
   - System running without errors

### Phase 3: EDF File Integration Testing

#### Test 3.1: EDF Loading with Gaze Active
1. **Preparation**: Ensure gaze mode is active from Test 2.3
2. **Test Various EDF Files**:
   - Small files (<1 hour)
   - Large files (>8 hours)  
   - Different channel counts (19, 32, 64+ channels)
   - Different sampling rates (256 Hz, 512 Hz, 1000 Hz)
3. **Verify**: 
   - Files load normally
   - Gaze system adapts to file parameters
   - No memory leaks or performance issues

#### Test 3.2: Channel Navigation Testing
1. Load multi-channel EDF file
2. Test channel scrolling (up/down arrows)
3. Test channel selection dialog (Ctrl+C)
4. **Verify**: Gaze coordinate mapping updates correctly

#### Test 3.3: Time Navigation Testing
1. Load EDF file > 30 seconds
2. Test time navigation:
   - Arrow keys (left/right)
   - Click and drag on time axis
   - Go to specific time (G key)
3. **Verify**: Gaze tracking adapts to time window changes

### Phase 4: Enhanced Features Testing

#### Test 4.1: Enhanced Auto-Scroll
1. Load EDF file with >2 minutes of data
2. Go to `Gaze → Enhanced Auto-Scroll` (Ctrl+Shift+A)
3. **Expected Behavior**:
   - Auto-scroll starts (like normal auto-scroll)
   - Status bar shows progress updates
   - Mock fixations may cause brief pauses
   - Can be stopped with same menu item

#### Test 4.2: Analytics Viewing
1. After running gaze mode for >30 seconds
2. Go to `Gaze → View Analytics`
3. **Expected**: Dialog showing:
   - Review speed metrics
   - Annotation statistics  
   - Fixation quality scores
   - Session duration

#### Test 4.3: Annotation Integration
1. Enable gaze mode with auto-annotations
2. Let system run for 1-2 minutes
3. Check annotation list (existing annotation features)
4. **Expected**: Some automatic annotations may be created
5. **Verify**: Annotations integrate with existing annotation system

### Phase 5: Real-World Workflow Testing

#### Test 5.1: Typical Clinical Review Session
**Scenario**: Simulate normal EEG review workflow
1. Load patient EDF file
2. Enable gaze tracking  
3. Perform typical review tasks:
   - Scroll through recording
   - Adjust sensitivity
   - Change time scales
   - Add manual annotations
   - Use screenshot function
4. **Verify**: All normal functions work with gaze active

#### Test 5.2: Performance Under Load
**Scenario**: Test with challenging files
1. Load largest available EDF file
2. Enable gaze tracking
3. Rapid navigation:
   - Quick time jumps
   - Fast channel scrolling
   - Rapid sensitivity changes
4. **Monitor**: 
   - Response time remains acceptable
   - Memory usage stable
   - No error messages

#### Test 5.3: Extended Session Testing
**Scenario**: Long-term stability
1. Start gaze tracking session
2. Leave running for 30+ minutes with periodic interaction
3. **Monitor**:
   - Memory usage over time
   - Performance degradation
   - Error accumulation

### Phase 6: Error Handling Testing

#### Test 6.1: Graceful Degradation
1. **Test Without Gaze Hardware**: 
   - Try `Gaze → Setup Gaze Tracking` without eye tracker
   - **Expected**: Clear error message, normal operation continues
2. **Test Invalid Configurations**:
   - Enter extreme values in setup dialog
   - **Expected**: Validation errors, safe defaults applied

#### Test 6.2: Recovery Testing
1. Start gaze tracking
2. Deliberately cause errors:
   - Load corrupted EDF file
   - Rapidly change configurations
   - Force Qt application events
3. **Expected**: System recovers gracefully, provides useful error messages

### Phase 7: Integration with Existing Features

#### Test 7.1: Session Save/Load
1. Configure gaze tracking with specific settings
2. Save session (Ctrl+S)
3. Close and reopen application
4. Load session (Ctrl+L)
5. **Verify**: Gaze settings preserved (or gracefully disabled)

#### Test 7.2: Screenshot with Gaze
1. Enable gaze mode
2. Take screenshot using existing screenshot tool
3. **Verify**: 
   - Screenshot works normally
   - Gaze overlays may or may not appear (depends on implementation)
   - No corruption or errors

#### Test 7.3: Keyboard Shortcuts
1. Test all existing keyboard shortcuts with gaze active
2. Test new gaze-specific shortcuts:
   - Ctrl+G (Setup Gaze)
   - Ctrl+Shift+G (Toggle Gaze Mode)
   - Ctrl+Shift+A (Enhanced Auto-Scroll)
3. **Verify**: No conflicts, all shortcuts work as expected

## Expected Results Summary

### ✅ What Should Work Perfectly
- **Normal EDF Viewing**: All existing functionality unchanged
- **Gaze Setup**: Mock tracker configuration works smoothly
- **Basic Integration**: Gaze tracking runs without interfering with normal workflow
- **Performance**: No noticeable performance impact
- **Error Handling**: Clear error messages, graceful degradation

### ⚠️ What Might Need Adjustment
- **Auto-Annotation Rules**: May need tuning for your specific EEG patterns
- **Enhanced Auto-Scroll Speed**: May need adjustment for your review preferences  
- **Visual Feedback**: Overlay positions might need fine-tuning for your screen setup

### 🔧 What Requires Real Hardware
- **Actual Gaze Cursor**: Only visible with real eye tracker
- **True Fixation Detection**: Mock tracker simulates fixations randomly
- **Calibration Workflow**: Requires hardware-specific calibration
- **Performance Optimization**: Real hardware may have different performance characteristics

## Troubleshooting Common Issues

### Issue 1: "Gaze tracking components not available"
**Cause**: Import error or missing dependencies
**Solution**: 
1. Check Python path in error logs
2. Verify all files in `src/gaze_tracking/` and `src/ui/` exist
3. Run `python test_integration.py` for detailed diagnosis

### Issue 2: Performance degradation
**Cause**: Resource usage or configuration issues
**Solution**:
1. Check gaze tracking settings (reduce sampling rate)
2. Monitor memory usage
3. Disable auto-annotations temporarily

### Issue 3: Qt application errors
**Cause**: Signal-slot connection issues or threading problems
**Solution**:
1. Restart application
2. Check error logs for specific Qt errors
3. Try different gaze tracking configurations

## Success Criteria for Production Use

### Minimum Requirements ✅
- [ ] All 6 integration tests pass
- [ ] Application launches normally with gaze menu
- [ ] Can load and view EDF files with gaze tracking active
- [ ] No crashes or critical errors during normal use
- [ ] Performance impact <10% of baseline

### Recommended for Clinical Use ✅
- [ ] Extended session testing (>1 hour) passes
- [ ] Multiple EDF file formats tested successfully
- [ ] Error recovery testing completed
- [ ] Analytics features working correctly
- [ ] Documentation reviewed and understood by users

### Optimal Configuration ⚙️
- [ ] Real eye tracker hardware connected and calibrated
- [ ] Auto-annotation rules tuned for your EEG patterns
- [ ] User preferences configured for optimal workflow
- [ ] Performance optimized for your typical file sizes
- [ ] User training completed for gaze-enhanced features

## Next Steps After Testing

### 1. If All Tests Pass ✅
- **Production Deployment**: System is ready for clinical use
- **User Training**: Train users on gaze-enhanced features
- **Hardware Planning**: Consider real eye tracker hardware
- **Workflow Integration**: Develop gaze-enhanced protocols

### 2. If Issues Found ⚠️
- **Document Issues**: Record specific error conditions
- **Configuration Tuning**: Adjust settings for your environment
- **Selective Deployment**: Use features that work well, disable problematic ones
- **Iterative Testing**: Re-test after adjustments

### 3. Hardware Upgrade Path 🔧
- **Eye Tracker Selection**: Choose appropriate hardware (Tobii, EyeLink, etc.)
- **Calibration Procedures**: Develop calibration workflows
- **Advanced Features**: Implement hardware-specific enhancements
- **Performance Optimization**: Optimize for real-time hardware data

## Conclusion

This gaze tracking integration provides significant enhancements to your EDF Viewer while maintaining full backward compatibility. The comprehensive testing procedures ensure reliable operation in your specific environment, and the modular design allows for selective feature adoption based on your needs and available hardware.

The system is designed to grow with your requirements, from basic mock testing to full clinical deployment with advanced eye tracking hardware.