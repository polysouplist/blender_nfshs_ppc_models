# Tool developed by PolySoupList

import sys
import os
import struct
import json


def parse_binary_to_dict(file_path: str):
	if not os.path.isfile(file_path):
		print(f"Error: File not found: {file_path}")
		sys.exit(1)
	
	with open(file_path, "rb") as f:
		header = f.read(0x110)
		num_cars = struct.unpack('<I', f.read(0x4))[0]
		
		cars = []
		
		for i in range(num_cars):
			name_bytes = f.read(0x104)
			Name = name_bytes.decode('ansi').rstrip('\x00')
			
			car = {
				"Name": Name,
				"Level Information": {},
				"Class": None
			}
			
			for j in range(4):	# 4 levels
				GearCount = struct.unpack('<I', f.read(0x4))[0]
				SpeedScore = struct.unpack('<I', f.read(0x4))[0]
				GripScore = struct.unpack('<I', f.read(0x4))[0]
				AccelatorScore = struct.unpack('<I', f.read(0x4))[0]
				BrakeScore = struct.unpack('<I', f.read(0x4))[0]
				BrakeDecreaseRPMPerSec = struct.unpack('<I', f.read(0x4))[0]
				
				GearInformation = {}
				for k in range(6):
					MinumumRPM = struct.unpack('<I', f.read(0x4))[0]
					MaximumRPM = struct.unpack('<I', f.read(0x4))[0]
					MinimumVelocity = struct.unpack('<I', f.read(0x4))[0]
					MaximumVelocity = struct.unpack('<I', f.read(0x4))[0]
					IncreaseRPMPerSecond = struct.unpack('<I', f.read(0x4))[0]
					DecreaseRPMPerSecond = struct.unpack('<I', f.read(0x4))[0]
					
					GEAR = f"GEAR {k + 1}"
					GearInformation[GEAR] = {
						"Minumum RPM": MinumumRPM,
						"Maximum RPM": MaximumRPM,
						"Minimum Velocity": MinimumVelocity,
						"Maximum Velocity": MaximumVelocity,
						"Increase RPM Per Second": IncreaseRPMPerSecond,
						"Decrease RPM Per Second": DecreaseRPMPerSecond
					}
				
				Price = struct.unpack('<I', f.read(0x4))[0]
				
				LEVEL = f"LEVEL {j + 1}"
				car["Level Information"][LEVEL] = {
					"Gear Count": GearCount,
					"Speed Score": SpeedScore,
					"Grip Score": GripScore,
					"Accelator Score": AccelatorScore,
					"Brake Score": BrakeScore,
					"Brake Decrease RPM Per Sec": BrakeDecreaseRPMPerSec,
					"Gear Information": GearInformation,
					"Price": Price
				}
			
			Class = struct.unpack('<I', f.read(0x4))[0]
			car["Class"] = Class
			
			cars.append(car)
	
	return {
		"Car Info File": cars
	}


def write_dict_to_binary(data: dict, output_path: str):
	with open(output_path, "wb") as f:
		
		# Writing header
		f.write(b'\xB8\x1E\x05\x3E\xD2\x07\x03\x00\x07\x00\x06\x00\x31\x00\x00\x00')
		f.write(b'\x00\x00\x97\x5D\x00\xE8\x4E\x00\x46\x0E\x5F\x17\xE1\x1C\x57\x17')
		f.write(b'\x48\x80\x0C\x00\x3E\x09\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00')
		f.write(b'\x02\x00\xDE\xC0\x00\x00\x06\x00\xDA\x2F\x87\x16\xC4\x09\xF7\xBF')
		f.write(b'\x67\x01\x00\x00\x00\x00\x68\x00\x6F\x01\x00\x00\x58\xBE\x43\x00')
		f.write(b'\x00\x00\x00\x00\x74\xF0\x68\x00\x90\x83\x43\x00\xFF\xFF\xFF\xFF')
		f.write(b'\x00\xF0\x68\x00\x9E\xBC\x41\x00\x0F\x00\x00\x00\x00\x00\x00\x00')
		f.write(b'\x90\xBE\x43\x00\xFC\xEF\x68\x00\x0F\x00\x00\x00\x00\x00\x00\x00')
		f.write(b'\x20\xF0\x68\x00\x26\x8F\x42\x00\x0F\x00\x00\x00\x00\x00\x00\x00')
		f.write(b'\x00\x00\x00\x00\xEC\x08\x2E\x01\x0F\x00\x00\x00\x60\x01\x56\x00')
		f.write(b'\x80\xF0\x68\x00\x04\xAD\x41\x00\x0F\x00\x00\x00\x00\x00\x00\x00')
		f.write(b'\x07\x00\x00\x00\xA4\xF0\x68\x00\x14\x81\x00\x00\xF0\xF0\x68\x00')
		f.write(b'\x68\x06\x00\x00\x0C\x00\x00\x00\x00\x00\x00\x00\x8C\x69\x1D\x01')
		f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x24\x1D\x43\x00')
		f.write(b'\x0C\x00\x00\x00\xA4\xF0\x68\x00\x14\x81\x00\x00\x60\x01\x56\x00')
		f.write(b'\x34\xF0\x68\x00\xD8\xF0\x68\x00\x18\x83\x43\x00\x00\x00\x00\x00')
		f.write(b'\x9C\xF0\x68\x00\x0D\xAF\x41\x00\x00\x00\x00\x00\x68\x06\x00\x00')
		
		cars = data.get("Car Info File", [])
		num_cars = len(cars)
		f.write(struct.pack('<I', num_cars))
		
		for car in cars:
			name = car.get("Name", "")
			name_bytes = name.encode('ansi')[:0x104]
			name_padded = name_bytes.ljust(0x104, b'\x00')
			f.write(name_padded)
			
			levels = car.get("Level Information", {})
			for k in range(1, 5):
				level_key = f"LEVEL {k}"
				level = levels.get(level_key, {})
				
				f.write(struct.pack('<I', level.get("Gear Count", 0)))
				f.write(struct.pack('<I', level.get("Speed Score", 0)))
				f.write(struct.pack('<I', level.get("Grip Score", 0)))
				f.write(struct.pack('<I', level.get("Accelator Score", 0)))
				f.write(struct.pack('<I', level.get("Brake Score", 0)))
				f.write(struct.pack('<I', level.get("Brake Decrease RPM Per Sec", 0)))
				
				gears = level.get("Gear Information", {})
				for g in range(1, 7):
					gear_key = f"GEAR {g}"
					gear = gears.get(gear_key, {})
					f.write(struct.pack('<I', gear.get("Minumum RPM", 0)))
					f.write(struct.pack('<I', gear.get("Maximum RPM", 0)))
					f.write(struct.pack('<I', gear.get("Minimum Velocity", 0)))
					f.write(struct.pack('<I', gear.get("Maximum Velocity", 0)))
					f.write(struct.pack('<I', gear.get("Increase RPM Per Second", 0)))
					f.write(struct.pack('<I', gear.get("Decrease RPM Per Second", 0)))
				
				f.write(struct.pack('<I', level.get("Price", 0)))
			
			f.write(struct.pack('<I', car.get("Class", 0)))
	
	return 0


def main():
	if len(sys.argv) != 2:
		print("Usage:")
		print("python NFSCarEditor.py <*.CIF>	Parse a CarInfoFile")
		print("python NFSCarEditor.py <*.json>	Generate a CarInfoFile")
		sys.exit(1)
	
	input_path = sys.argv[1]
	
	if input_path.lower().endswith('.json'):
		print(f"Info: generating a file %s" % input_path)
		with open(input_path, "r", encoding="utf-8") as f:
			data = json.load(f)
		
		output_path = os.path.splitext(input_path)[0] + ".CIF"
		write_dict_to_binary(data, output_path)
		
		print(f"Info: finished generating a file %s" % output_path)
	
	else:
		print("Info: parsing a file %s" % input_path)
		data = parse_binary_to_dict(input_path)
		
		output_path = os.path.splitext(input_path)[0] + ".json"
		with open(output_path, "w", encoding="utf-8") as f:
			json.dump(data, f, indent='\t', ensure_ascii=False)
		
		print(f"Info: finished parsing a file %s" % output_path)


if __name__ == "__main__":
	main()
