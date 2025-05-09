FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies with clean cache and force reinstall
RUN npm cache clean --force && \
    npm install --no-cache --force && \
    npm install react-router-dom@6.10.0

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]