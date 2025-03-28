const amqp = require("amqplib");
const axios = require("axios");
const RABBITMQ_URL = "amqp://rabbitmq:5672";  // Use 'rabbitmq' as the service name in Docker Compose
const QUEUE_NAME = "booking_queue";
const USER_SERVICE_URL = "http://event-service.onlineeventbookingamaar.svc.cluster.local:8000/users";
const { SendEmail } = require("./send_email");
const dotenv = require("dotenv");

dotenv.config();

async function fetchUserDetails(userId) {
    try {
        const response = await axios.get(`${USER_SERVICE_URL}/${userId}`);
        return response.data;
    } catch (error) {
        console.error(`❌ Failed to fetch user details for ID ${userId}:`, error.response?.data || error.message);
        return null;
    }
}

async function startConsumer() {
    try {
        console.log('🚀 Trying to connect to RabbitMQ...');
        const connection = await amqp.connect(RABBITMQ_URL);
        const channel = await connection.createChannel();

        await channel.assertQueue(QUEUE_NAME, { durable: true });
        console.log(`✅ Connected to RabbitMQ and waiting for messages in queue: ${QUEUE_NAME}...`);

        channel.consume(QUEUE_NAME, async (msg) => {
            if (msg !== null) {
                const message = JSON.parse(msg.content.toString());
                console.log(`✅ Booking confirmed for user`, message);

                // Fetch user details using user_id
                const user = await fetchUserDetails(message.user_id);

                if (user) {
                    console.log(`📧 Sending email to ${user.email}...`);

                    SendEmail({
                        email: user.email,
                        userName: user.username,
                        emailType: "booking_confirmation",
                        noOfTickets: message.no_of_ticket,
                        amount: message.ammount
                    });

                    console.log(`📩 Email sent successfully to ${user.email}`);
                } else {
                    console.log(`⚠️ User details not found for user_id: ${message.user_id}`);
                }

                // Acknowledge the message
                channel.ack(msg);
            }
        });
    } catch (error) {
        console.error("❌ Error connecting to RabbitMQ:", error);
        // Retry connection after a delay (e.g., 5 seconds)
        setTimeout(startConsumer, 5000);  // Retry connection after 5 seconds
    }
}

startConsumer();

