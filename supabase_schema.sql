-- Run this script in Supabase SQL editor to create required tables/indexes

create table if not exists users (
    user_id bigint primary key,
    chat_id bigint not null,
    username text,
    first_name text,
    last_name text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists wallets (
    id serial primary key,
    wallet_address text not null,
    user_id bigint not null references users(user_id),
    added_at timestamptz default now(),
    last_processed_block bigint default 0,
    is_active boolean default true,
    unique (wallet_address, user_id)
);

create table if not exists transactions (
    id serial primary key,
    wallet_address text not null,
    tx_hash text not null unique,
    tx_type text not null,
    from_address text,
    to_address text,
    value text,
    token_address text,
    token_symbol text,
    token_name text,
    token_id text,
    function_name text,
    block_number bigint,
    gas_used bigint,
    created_at timestamptz default now()
);

create table if not exists balance_history (
    id serial primary key,
    wallet_address text not null,
    token_address text,
    balance text not null,
    balance_eth double precision,
    block_number bigint,
    created_at timestamptz default now()
);

create index if not exists idx_wallets_address on wallets(wallet_address);
create index if not exists idx_wallets_user on wallets(user_id);
create index if not exists idx_transactions_wallet on transactions(wallet_address);
create index if not exists idx_transactions_hash on transactions(tx_hash);
create index if not exists idx_balance_wallet on balance_history(wallet_address);

