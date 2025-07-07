# 🚀 Quick Setup Guide

Get PVE up and running in under 5 minutes!

## Prerequisites

- **Docker & Docker Compose** (recommended)
- **Git** for cloning the repository

## 🐳 Quick Start with Docker

### 1. Clone & Setup
```bash
git clone https://github.com/Yak0vkaSup/pve
cd pve
cp env.example .env
```

### 2. Configure Required Environment Variables

Edit `.env` file with your configurations:

```bash
# REQUIRED: Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=123456:your_actual_bot_token_here

# REQUIRED: Generate with: openssl rand -hex 64
JWT_SECRET=your_generated_jwt_secret_here

# OPTIONAL: Only needed for live trading
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_secret
```

### 3. Start the Platform
```bash
docker-compose up -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **API**: http://localhost:5001
- **Database**: localhost:5432

## 🔧 Configuration Steps

### Step 1: Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create a new bot
4. Copy the token and add it to your `.env` file

### Step 2: Generate JWT Secret

```bash
# Generate a secure JWT secret
openssl rand -hex 64
```

Add this to your `.env` file as `JWT_SECRET`

### Step 3: (Optional) Bybit API Setup

For live trading, you'll need Bybit API credentials:

1. Go to [Bybit API Management](https://www.bybit.com/app/user/api-management)
2. Create a new API key with **trading permissions only** (no withdrawal)
3. Add IP restrictions for security
4. Add the keys to your `.env` file

## 🎮 First Steps

### 1. Login
- Open http://localhost:3000
- Click the Telegram login button
- Authenticate with your Telegram account

### 2. Create Your First Strategy
- Go to the "Factory" tab
- Use the visual node editor to create a simple strategy
- Try connecting: `Market Data → RSI → Compare → Buy/Sell Signal`

### 3. Backtest
- Set a date range and symbol (e.g., BTCUSDT)
- Click "Run Backtest"
- View results in the analytics dashboard

### 4. (Optional) Deploy Live Bot
- Go to the "Port" tab
- Create a new bot with your strategy
- Configure position size and risk parameters
- Start the bot (ensure you have Bybit API configured)

## 🛠️ Development Setup

If you want to develop or modify PVE:

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python pve/run.py
```

### Frontend Development
```bash
npm install
npm run dev
```

## 🔧 Troubleshooting

### Common Issues

#### "TELEGRAM_BOT_TOKEN not found"
- Make sure you copied `env.example` to `.env`
- Verify your bot token is correctly set in `.env`

#### "Cannot connect to database"
- Wait a minute for PostgreSQL to fully start up
- Check if PostgreSQL container is running: `docker ps`

#### "Frontend not loading"
- Check if all services are running: `docker-compose ps`
- Look at logs: `docker-compose logs webserver`

#### "Bot not executing trades"
- Verify Bybit API credentials are correct
- Check if your API key has trading permissions
- Ensure sufficient balance in your account

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the main README.md
- **Community**: Join our Discord/Telegram community

## 🚨 Security Reminders

- **Never commit** your `.env` file
- **Start small** when testing live trading
- **Use read-only API keys** for testing when possible
- **Set strict position limits** in your strategies
- **Monitor your bots** regularly

## 📈 Next Steps

Once you have PVE running:

1. **Learn the nodes**: Explore different technical indicators
2. **Study examples**: Check out template strategies
3. **Join the community**: Connect with other algorithmic traders
4. **Contribute**: Help improve PVE with your own nodes and features

---

**Ready to build your first trading strategy? Let's go! 🚀** 