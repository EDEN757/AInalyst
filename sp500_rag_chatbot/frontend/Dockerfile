FROM node:16-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Start the app
CMD ["npm", "start"]
