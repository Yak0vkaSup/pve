import http from 'http'
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import bodyParser from 'body-parser';
import jwt from 'jsonwebtoken';

const secretKey = '2bc4d44e9ee1c83cd764e54658bc5db3c2ef9223943d88e8c30035b0471466ece5b2bab3c1095e905444851f84f2672e72f650a5035e1dad363bfaf026ea745a';

const app = express();
const port = 3000;
const host = '0.0.0.0';

// Middlewarenod
app.use(bodyParser.json()); // For parsing JSON data

// Serve static files
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
app.use(express.static(path.join(__dirname, '..', 'dist')));


// Telegram authentication handler
app.post('/auth/telegram', (req, res) => {
    const userData = req.body;

    // Validate the received data (you can add more validation here)
    if (!userData || !userData.id || !userData.hash) {
        return res.status(400).json({ message: 'Invalid Telegram data' });
    }

    // Generate JWT token after validating Telegram auth data
    const token = jwt.sign(
        { id: userData.id, firstName: userData.first_name, username: userData.username },
        secretKey,
        { expiresIn: '24h' } // Token expires in 1 hour
    );

    // Send token back to the client
    res.json({ success: true, token });
});

// Fallback for SPA
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
});

http.createServer(app).listen(port, host, () => {
    console.log(`Server is running on https://0.0.0.0:${port}`);
});
