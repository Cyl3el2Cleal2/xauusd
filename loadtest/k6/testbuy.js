import http from 'k6/http';
import { check, sleep } from 'k6';

// 1. Define the configuration
export const options = {
    iterations: 100, // Exactly 1000 total requests
    vus: 4,          // 10 concurrent users
};

export default function () {
    const url = 'http://localhost:8000/trading/buy';

    // 2. Setup the payload
    const payload = JSON.stringify({
        symbol: 'gold96',
        amount: 3500,
    });

    // 3. Setup the headers
    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MjExZjk0Mi0yMjY5LTQxZTctODFiYi1jYmIzNWY3ZGFhZDkiLCJhdWQiOlsiZmFzdGFwaS11c2VyczphdXRoIl0sImV4cCI6MTc2NzEwMzM2Mn0.ePsyBYFa8qdw2Qmi0MrLhTO24gKz40A7Uckk9-gksDg',
            'Accept': 'application/json',
            'User-Agent': 'k6-load-test',
        },
    };

    // 4. Perform the POST request
    const res = http.post(url, payload, params);

    // 5. Optional: Validate response
    check(res, {
        'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
        'transaction successful': (r) => r.body.includes('gold96'),
    });

    // Small sleep to prevent overwhelming a local dev machine too instantly
    // Remove this if you want maximum speed
    sleep(0.1);
}