FROM node:16-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Fix permissions issues
RUN mkdir -p node_modules/.cache && chmod -R 777 node_modules/.cache

# Start the app
CMD ["npm", "start"]
