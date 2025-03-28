# Use a minimal Node.js base image
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first for better caching
COPY package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Copy the rest of the application files
COPY . .

# Load environment variables from .env file
COPY .env .env

# Expose port 4000 for the Event Service
EXPOSE 4000

# Command to start the Event Service
CMD ["node", "index.js"]
