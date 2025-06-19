# Library Service API

A comprehensive Django REST Framework-based library management system that allows users to borrow books, manage returns, process payments, and receive notifications via Telegram.

## Features

- **User Authentication**: Secure user registration and authentication system
- **Book Management**: Add, update, and manage book inventory
- **Borrowing System**: Borrow books with expected return dates
- **Return Processing**: Staff can process book returns
- **Fine Management**: Automatic fine calculation for late returns
- **Payment Integration**: Process payments for fines and fees
- **Telegram Notifications**: Real-time notifications to users via Telegram bot
- **Admin Dashboard**: Comprehensive admin interface for library staff
- **Filtering and Searching**: Advanced filtering options for books and borrowings

## Tech Stack

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Caching/Messaging**: Redis
- **Asynchronous Tasks**: Celery
- **Web Server**: Gunicorn, Nginx
- **Containerization**: Docker, Docker Compose
- **Notification**: Telegram Bot API
- **Development Tools**: Flake8, Pytest

## Installation

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (for notifications)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/drf-library-service.git
   cd drf-library-service
   ```

2. Create a `.env` file based on the `.env.sample`:
   ```bash
   cp .env.sample .env
   ```

3. Update the `.env` file with your configuration:
   - Database credentials
   - Telegram Bot Token
   - Secret key
   - Other environment-specific settings

4. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

5. The API will be available at http://localhost:80

## Usage

### API Endpoints

#### Authentication
- `POST /api/v1/auth/register/`: Register a new user
- `POST /api/v1/auth/token/`: Get JWT token

#### Books
- `GET /api/v1/books/`: List all books
- `POST /api/v1/books/`: Add a new book (admin only)
- `GET /api/v1/books/{id}/`: Get book details
- `PUT /api/v1/books/{id}/`: Update book (admin only)
- `DELETE /api/v1/books/{id}/`: Delete book (admin only)

#### Borrowings
- `GET /api/v1/borrowings/`: List user's borrowings (or all for admin)
- `POST /api/v1/borrowings/`: Borrow a book
- `GET /api/v1/borrowings/{id}/`: Get borrowing details
- `POST /api/v1/borrowings/{id}/return_borrowing/`: Return a book (admin only)

#### Payments
- `GET /api/v1/payments/`: List user's payments
- `GET /api/v1/payments/{id}/`: Get payment details
- `POST /api/v1/payments/{id}/success/`: Process successful payment
- `POST /api/v1/payments/{id}/cancel/`: Cancel payment

## Development

### Running Tests
```bash
python manage.py test
```

### Code Linting
```bash
flake8 .
```

## Telegram Bot Integration

The system includes a Telegram bot for notifications. Users can:
1. Link their account to receive notifications
2. Get notified about:
   - Successful borrowings
   - Upcoming return dates
   - Payment confirmations

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
