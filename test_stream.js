const http = require('http');
const req = http.request({
  hostname: 'localhost',
  port: 3000,
  path: '/api/chat/stream',
  method: 'POST',
  headers: {'Content-Type': 'application/json'}
}, (res) => {
  res.on('data', (c) => console.log('CHUNK:', c.toString()));
});
req.write(JSON.stringify({message: 'hello', user_id: 'test', session_id: 'test', preferred_sources: []}));
req.end();
