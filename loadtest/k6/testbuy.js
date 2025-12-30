import http from 'k6/http';
import { check, sleep } from 'k6';

const JWT = 'changeit'
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
            'Authorization': `Bearer ${JWT}`,
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