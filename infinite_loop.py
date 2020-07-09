import os, time

i = 0
t = 0.3
print('Infinite loop launch!')
for _ in range(5):  # while True:
    time.sleep(t)
    i += 1
    print(f'after {t} seconds. iteration {i}')

print('Done!')
