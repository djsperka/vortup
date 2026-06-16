# This is intial code to read data dimension and extract B-scan data and A-line profile
# Worked on June 11 2026
import numpy as np
import sys
import os
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

#npy_file = sys.argv[1]
npy_file = sys.argv[1]

data = np.load(npy_file)

print("Type :", type(data))
print("Shape:", data.shape) # Output example: (depth, rows, cols)
print("Dtype:", data.dtype)

data = np.squeeze(data)
print(data.shape)  
#A-scan, B-scan and 
#     clean_data = data[0, :, :, :, 0]
no_of_Bscan=data.shape[0]
no_of_Ascan=data.shape[1]
Ascan_length=data.shape[2]
print('Number of A-scans:', no_of_Ascan)
print('Number of B-scans:', no_of_Bscan)
print('A-scan length:', Ascan_length)

plt.ion()  # interactive mode

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
plt.tight_layout(pad=2.5)
            

for i in range(no_of_Bscan):
    
    bscan = data[i, :, :]      # change in B-scan number # shape: A-scan x depth
    mean_ascan = np.mean(data[i,:,:], axis=0) # average over A-scans
    
    ax1.clear()
    ax1.imshow( (bscan.T.astype(np.float32) + 1), aspect='auto',cmap='gray')
    ax1.set_title(f'B-scan {i+1}/{no_of_Bscan}')
    ax1.set_xlabel("A-scan")
    ax1.set_ylabel("Depth")
    
    ax2.clear()
    ax2.plot(mean_ascan.T)
    ax2.set_title(f'Mean A-scan: B-scan {i+1}/{no_of_Bscan}')
    ax2.set_xlabel('Depth Sample')
    ax2.set_ylabel('Mean Intensity')

    plt.pause(0.01)


plt.ioff()

plt.show()