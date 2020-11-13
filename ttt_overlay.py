"""
The code function is used to analyze Team Time Trial individual effort on the pull. The code can spot the pull and
show the average power/HR/Cadence etc. And finally highlight the pull period on the chart.
There are three parameters required for the analysis,
- user_weight in KG,
- sample_time which indicates how much time in seconds each rider pull at front
- sample_avg_wkg is a target wkg you believe the rider is pulling during that time, the code still not does complex
analysis on spoting the peak of pull, so now user need to provide a number so the code can figure out the pull.
You can tune this number to a bit lower or higher to trim some outliers.
- filename, the ride FIT file
"""
import fitdecode
import numpy as np
from datetime import timedelta
from pytz import timezone
import matplotlib.pyplot as plt

user_weight = 95.25 # 62.7 # Travis 88.45 # Eric 95.25
sample_time = 30  # how many seconds we sample for pull
sample_avg_wkg = 4.5  # find any period of time that average is over ? wkg
filename = "Frappe_10th_.fit"


def convert_meter_sec_to_mile_hour(meter):
    return meter * 60 * 60 * 0.000621371


def find_pull(tmp_single_sample_data, sample_time, new_power, sample_avg_wkg, user_weight):
    """
    this is a rough finding of the data, refine_pull will do a better job over the data finding here, truly can
    combine two codes into one function but can be very complex to understand the logic after.
    """
    tmp_single_sample_data.append(new_power)
    if len(tmp_single_sample_data) == sample_time:
        tmp_single_sample_data.pop(0)
        if np.mean(tmp_single_sample_data)/user_weight >= sample_avg_wkg:
            return np.mean(tmp_single_sample_data)/user_weight
        return None
        
        
def refine_pull(sample_data, timestamp_list, hr_list, speed_list, cadence_list):
    """
    over the rough finding sample data from find_pull, here we find the best average wkg over period of time that
    hitting target wkg and pick the best over them.
    """
    tmp_power = []
    tmp_start = None
    final_pull = []
    last_start_time_idx = -1
    for one_wkg, start_time_idx, end_time_idx in sample_data:
        if start_time_idx <= last_start_time_idx:
            continue
        start_time = timestamp_list[start_time_idx]
        avg_hr = np.mean(hr_list[start_time_idx: end_time_idx+1])
        avg_speed = np.mean(speed_list[start_time_idx: end_time_idx+1])
        avg_cadence = np.mean(cadence_list[start_time_idx: end_time_idx+1])
        if not tmp_power:
            tmp_power.append((one_wkg, avg_hr, avg_speed, avg_cadence, start_time_idx, end_time_idx))
            tmp_start = start_time
            continue
        
        if tmp_start + timedelta(seconds=1) == start_time:
            tmp_start = start_time
            tmp_power.append((one_wkg, avg_hr, avg_speed, avg_cadence, start_time_idx, end_time_idx))
        else:
            sorted_tmp_power = sorted(tmp_power, key=lambda x: x[0])
            best_power = sorted_tmp_power.pop()
            final_pull.append(best_power)
            tmp_power = []
            last_start_time_idx = best_power[4]
    return final_pull
    

with fitdecode.FitReader(filename) as fit:
    timestamp_list = []
    timestamp_xticks = []
    power_list = []
    hr_list = []
    speed_list = []
    cadence_list = []
    sample_data = []
    tmp_single_sample_data = []
    
    for frame in fit:
        if isinstance(frame, fitdecode.FitDataMessage):
            # Here, frame is a FitDataMessage object.
            # A FitDataMessage object contains decoded values that
            # are directly usable in your script logic.
            if frame.name == "record":
                new_power = frame.get_value("power")
                power_list.append(new_power)
                speed = frame.get_value("enhanced_speed")
                speed_list.append(speed)
                hr_list.append(frame.get_value("heart_rate"))
                cadence_list.append(frame.get_value("cadence"))
                ride_time = frame.get_value("timestamp").astimezone(timezone('US/Pacific'))
                if ride_time.second == 0 and ride_time.minute % 5 == 0:
                    timestamp_xticks.append(ride_time.strftime("%H:%M:%S"))
                timestamp_list.append(ride_time)

                possible_sample_data = find_pull(tmp_single_sample_data, sample_time, new_power, sample_avg_wkg, user_weight)
                if possible_sample_data:
                    sample_data.append((possible_sample_data, len(timestamp_list) - sample_time, len(timestamp_list) - 1))
                    

# Print data
print("WKG, AVG_HR, AVG_SPD, AVG_CADENCE, START, END")
refined_pull_data = refine_pull(sample_data, timestamp_list, hr_list, speed_list, cadence_list)
for power, hr, speed, cadence,  start, end in refined_pull_data:
    print("{}, {}, {}, {}, {}, {}".format(round(power, 2),
                                          int(hr),
                                          round(convert_meter_sec_to_mile_hour(speed), 2),
                                          round(cadence, 2),
                                          timestamp_list[start].strftime("%H:%M:%S"),
                                          timestamp_list[end].strftime("%H:%M:%S")))

# plot the graph of pull
timestamp_list = [ts.strftime("%H:%M:%S") for ts in timestamp_list]
fig, ax = plt.subplots(figsize=(18, 6))

last_end = 0
for i, one_pull in enumerate(refined_pull_data):
    # first pull data, plot the data before the first pull
    power, hr, speed, cadence, start, end = one_pull
    if last_end >= 0:
        ax.plot(timestamp_list[last_end:start-1], power_list[last_end:start-1], color='r')
    
    # plot pull data
    last_end = end+1
    ax.plot(timestamp_list[start:end], power_list[start:end], color='b')
    
    if i == len(refined_pull_data)-1:
        ax.plot(timestamp_list[end+1:], power_list[end+1:], color='r')

ax.set_xlabel('Time')
ax.set_ylabel("Power")
ax.set_xticks(timestamp_xticks)
plt.show()
