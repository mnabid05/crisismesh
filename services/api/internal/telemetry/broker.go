package telemetry

import (
	"context"
	"sync"

	"github.com/nats-io/nats.go"
)

type Event struct {
	Type string `json:"type"`
	Data any    `json:"data"`
}

type Broker interface {
	Publish(context.Context, []byte) error
	Subscribe() (<-chan []byte, func())
	Close()
}

type LocalBroker struct {
	mu          sync.RWMutex
	subscribers map[chan []byte]struct{}
}

func NewLocalBroker() *LocalBroker { return &LocalBroker{subscribers: map[chan []byte]struct{}{}} }
func (b *LocalBroker) Publish(_ context.Context, payload []byte) error {
	b.mu.RLock()
	defer b.mu.RUnlock()
	for ch := range b.subscribers {
		select {
		case ch <- payload:
		default:
		}
	}
	return nil
}
func (b *LocalBroker) Subscribe() (<-chan []byte, func()) {
	ch := make(chan []byte, 32)
	b.mu.Lock()
	b.subscribers[ch] = struct{}{}
	b.mu.Unlock()
	return ch, func() {
		b.mu.Lock()
		if _, ok := b.subscribers[ch]; ok {
			delete(b.subscribers, ch)
			close(ch)
		}
		b.mu.Unlock()
	}
}
func (b *LocalBroker) Close() {}

type NATSBroker struct {
	conn  *nats.Conn
	local *LocalBroker
	sub   *nats.Subscription
}

func NewNATSBroker(url string) (*NATSBroker, error) {
	conn, err := nats.Connect(url)
	if err != nil {
		return nil, err
	}
	b := &NATSBroker{conn: conn, local: NewLocalBroker()}
	b.sub, err = conn.Subscribe("crisismesh.incidents", func(msg *nats.Msg) { _ = b.local.Publish(context.Background(), msg.Data) })
	if err != nil {
		conn.Close()
		return nil, err
	}
	return b, nil
}
func (b *NATSBroker) Publish(_ context.Context, payload []byte) error {
	return b.conn.Publish("crisismesh.incidents", payload)
}
func (b *NATSBroker) Subscribe() (<-chan []byte, func()) { return b.local.Subscribe() }
func (b *NATSBroker) Close() {
	if b.sub != nil {
		_ = b.sub.Unsubscribe()
	}
	b.conn.Close()
}
