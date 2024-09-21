console.log('Hello world!');

const ws = new WebSocket('ws://localhost:8765');

// Обробка події при відправленні форми
formChat.addEventListener('submit', (e) => {
    e.preventDefault();  // Зупиняємо стандартну поведінку
    const message = textField.value;

    ws.send(message);
    displayChatMessage(`You: ${message}`);

    textField.value = '';
});


// Обробка події при відкритті з'єднання
ws.onopen = () => {
    console.log('Connected to WebSocket!');
};

// Обробка отриманих повідомлень
ws.onmessage = (e) => {
    console.log(e.data);
    
    // Перевіряємо чи це команда exchange, чи звичайне повідомлення
    if (e.data.startsWith('{') || e.data.startsWith('[')) {
        const rates = JSON.parse(e.data);
        displayExchangeRates(rates);
    } else {
        displayChatMessage(e.data);
    }
};

// Функція для відображення повідомлень у чаті
function displayChatMessage(message) {
    const elMsg = document.createElement('div');
    elMsg.textContent = message;
    document.getElementById('subscribe').appendChild(elMsg);
}

// Функція для відображення курсу валют
function displayExchangeRates(rates) {
    const container = document.getElementById('exchangeRates');
    container.innerHTML = '';

    rates.forEach(rateData => {
        for (const date in rateData) {
            const rateBlock = document.createElement('div');
            rateBlock.className = 'rate-block';

            const dateEl = document.createElement('h3');
            dateEl.textContent = `Date: ${date}`;
            rateBlock.appendChild(dateEl);

            const rateTable = document.createElement('table');
            rateTable.className = 'rate-table';
            
            const headerRow = document.createElement('tr');
            headerRow.innerHTML = `
                <th>Currency</th>
                <th>Sale</th>
                <th>Purchase</th>
            `;
            rateTable.appendChild(headerRow);

            const currencies = rateData[date];
            for (const currency in currencies) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${currency}</td>
                    <td>${currencies[currency].sale}</td>
                    <td>${currencies[currency].purchase}</td>
                `;
                rateTable.appendChild(row);
            }

            rateBlock.appendChild(rateTable);
            container.appendChild(rateBlock);
        }
    });
}
