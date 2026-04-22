import { faker } from "@faker-js/faker";
import { v4 as uuidv4 } from "uuid";

const generateFakeMessages = (count = 10) => {
  const messages = [];

  for (let i = 0; i < count; i++) {
    // We generate a random UUID for the message itself
    const messageId = uuidv4();

    // In a real scenario, you'd fetch these IDs from your 'conversations' table
    const conversationId = uuidv4();

    const fakeMessage = {
      id: messageId,
      conversation_id: conversationId,
      role: faker.helpers.arrayElement(["user", "consultant", "system"]),
      content: faker.lorem.sentence(),
      created_at: faker.date.recent({ days: 30 }).toISOString(),
      session_id: faker.string.alphanumeric(10),
      // message jsonb field: storing WhatsApp-style metadata
      message: {
        platform: "whatsapp",
        status: faker.helpers.arrayElement(["sent", "delivered", "read"]),
        metadata: {
          phone_number: faker.phone.number(),
          browser: faker.internet.userAgent(),
        },
      },
    };

    messages.push(fakeMessage);
  }

  return messages;
};

// Example Usage:
// const dummyData = generateFakeMessages(5);
// console.log(JSON.stringify(dummyData, null, 2));

export default generateFakeMessages;
