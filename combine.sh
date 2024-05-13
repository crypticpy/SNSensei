#!/bin/bash

# Define the directories where the script should look for Python files
DIRECTORIES=("$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )" "$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/app")

# Get the current date in a format suitable for filenames
CURRENT_DATE=$(date "+%Y-%m-%d")

# Initialize file name and increment
FILE_NUMBER=1
OUTPUT_FILE="${DIRECTORIES[0]}/combined_python_files_${CURRENT_DATE}_${FILE_NUMBER}.txt"

# Check if file already exists and increment FILE_NUMBER until it finds a new file name
while [ -f "$OUTPUT_FILE" ]; do
    FILE_NUMBER=$((FILE_NUMBER+1))
    OUTPUT_FILE="${DIRECTORIES[0]}/combined_python_files_${CURRENT_DATE}_${FILE_NUMBER}.txt"
done

# Create a temporary file for holding the map
MAP_FILE="${DIRECTORIES[0]}/map_file.txt"
echo "Content Map:" > $MAP_FILE

# Initialize a line counter
LINE_COUNTER=1

# Loop through each directory
for DIR in "${DIRECTORIES[@]}"; do
    # Loop through each Python file in the current directory
    for FILE in $DIR/*.py; do
        if [ -f "$FILE" ]; then # Check if the file is a regular file
            # Get the relative path of the file
            RELATIVE_PATH="${FILE#${DIR}/}"

            # Print the file name and relative path as a header in the output file
            echo "Filename: $RELATIVE_PATH" >> $OUTPUT_FILE
            echo "--------------------------------" >> $OUTPUT_FILE

            # Add the current file and its starting line to the map
            echo "$RELATIVE_PATH: Starts at line $LINE_COUNTER" >> $MAP_FILE

            # Append the file content to the output file
            cat "$FILE" >> $OUTPUT_FILE
            echo "" >> $OUTPUT_FILE # Ensure there is a blank line after each file's content

            # Update the line counter with the number of lines of the current file plus three
            # (one for the filename header, one for the separator, and one for the blank line)
            LINE_COUNTER=$(($LINE_COUNTER + $(wc -l < "$FILE") + 3))
        fi
    done
done

# Prepend the map to the beginning of the output file
cat $MAP_FILE $OUTPUT_FILE > temp && mv temp $OUTPUT_FILE

# Clean up the temporary map file
rm $MAP_FILE

echo "All Python files have been combined into $OUTPUT_FILE with a content map at the beginning."


