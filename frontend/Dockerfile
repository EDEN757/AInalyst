FROM node:16-alpine

# Create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Set environment variable for API connection with fallbacks
ENV REACT_APP_API_URL http://host.docker.internal:8000

# Copy package.json and package-lock.json
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Create .cache directory and grant permissions
RUN mkdir -p node_modules/.cache && \
    chmod -R 777 node_modules/ && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Start the app
CMD ["npm", "start"]
