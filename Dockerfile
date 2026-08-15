FROM rabbitmq:3.13-management

# Install curl to download the plugin
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Download the community delayed message exchange plugin matching the RabbitMQ version
RUN curl -L -o /plugins/rabbitmq_delayed_message_exchange-3.13.0.ez \
    https://github.com/rabbitmq/rabbitmq-delayed-message-exchange/releases/download/v3.13.0/rabbitmq_delayed_message_exchange-3.13.0.ez

# Enable both the management UI and the delayed message exchange plugin
RUN rabbitmq-plugins enable --offline rabbitmq_delayed_message_exchange