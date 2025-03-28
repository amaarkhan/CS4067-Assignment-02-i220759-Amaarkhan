# Use the official Node.js image as the base image
FROM node:18

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the package.json and package-lock.json to the container
COPY package*.json ./

# Install dependencies inside the container
RUN npm install

# Copy the rest of the application code to the container
COPY . .


# Run the application
CMD ["npm", "start"]

