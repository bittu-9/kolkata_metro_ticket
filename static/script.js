function bookTicket() {
    window.location.href = '/book-form';
  }
  
  function showBookings() {
    fetch('/api/bookings')
      .then(res => res.json())
      .then(data => {
        if (data.length === 0) {
          alert("No bookings found.");
        } else {
          let msg = "Your Bookings:\n\n";
          data.forEach((ticket, index) => {
            msg += `${index + 1}. ${ticket.username} → ${ticket.from} to ${ticket.to} (ID: ${ticket.ticket_id})\n`;
          });
          alert(msg);
        }
      });
  }
  
  function cancelTicket() {
    const ticket_id = prompt("Enter Ticket ID to cancel:");
    if (!ticket_id) return;
  
    fetch('/api/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket_id })
    })
    .then(res => res.json())
    .then(data => alert(data.message));
  }
  