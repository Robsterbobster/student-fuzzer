from improved_student_fuzzer import get_results as i_results
from base_student_fuzzer import get_results as b_results
import numpy
import matplotlib.pyplot as plt
from lifelines.statistics import logrank_test as test

#Sample fuzzer performance 5 times
i_arr, i_events = i_results()
b_arr, b_events = b_results()
i_np_arr = numpy.array(i_arr)
b_np_arr = numpy.array(b_arr)
i_mean = i_np_arr.mean()
b_mean = b_np_arr.mean()
i_std = i_np_arr.std(ddof=1)
b_std = b_np_arr.std(ddof=1)
print()
print("Baseline mean: ", b_mean)
print("Baseline std: ", b_std)
print("Baseline variance: ", b_np_arr.var(ddof=1))
print("Improved mean: ", i_mean)
print("Improved std: ", i_std)
print("Improved variance: ", i_np_arr.var(ddof=1))

axis = ["Baseline", "Improved"]
x_pos = numpy.arange(len(axis))
means = [b_mean, i_mean]
errs = [b_std, i_std]
fig, ax = plt.subplots()
ax.bar(x_pos, means, yerr=errs, align='center', alpha=0.5, ecolor='black', capsize=10)
ax.set_ylabel('Time (s)')
ax.set_xticks(x_pos)
ax.set_xticklabels(axis)
ax.set_title('Fuzzer Peformance on Example Bug')
ax.yaxis.grid(True)

# Save the figure and show
plt.tight_layout()
plt.savefig('plot.png')

#check if overlaps

if i_mean < b_mean:
    if i_mean + i_std >= b_mean-b_std:
        print("There is overlap, perform test")
        results = test(b_arr, i_arr, event_observed_A=b_events, event_observed_B=i_events)
        if results.p_value < 0.05:
            print("Result is significant, improved fuzzer is better")
        else:
            print("Result is not significant, improved fuzzer is not better")
    else:
        print("Improved fuzzer is better")
else:
    print("Improved fuzzer is not better")