---
title: >-
  shelvez: a compressed, faster alternative to shelve with JSON and Pydantic
  support
abbrlink: 62db67aa
date: 2025-05-19 15:49:24
tags:
---

## What My Project Does

I made a small library called [`shelvez`](https://github.com/touxiaoling/shelvez). It works similarly to Python’s built-in `shelve`, but adds compression and flexible serialization options.

`shelvez` is a lightweight key-value store with:

* Zstandard compression for smaller database files
* Built-in support for Pickle, JSON, and Pydantic model serialization
* A plug-in serializer interface if you want to define your own
* Future plans for SQLite-backed transactions

The goal is to provide a more flexible and efficient alternative to `shelve`, while keeping the same simple API.

## Target Audience

This project may be useful for:

* Developers who like the convenience of `shelve` but want smaller and faster storage
* People building scripts, data pipelines, CLI tools, or experiments
* Anyone who wants to store structured data (like dicts or models) with minimal setup

It’s still early stage, so best suited for prototypes, research, or personal tools rather than production.

## Comparison

Compared to Python’s built-in `shelve`, `shelvez`:

Measured using `pytest-benchmark` with some number simple `db["random_key"] = random_value` writes:

|Backend|Mean Write Time|File Size|
|:-|:-|:-|
|`shelve`|\~450 ms|380 KB|
|`shelvez`|\~240–260 ms|308–312 KB|

>Roughly 2× faster and \~20% smaller on disk based on benchmarks using random string data. In real-world usage with more structured or repetitive data, compression is likely to be even more effective.

## Example Usage

```python
import shelvez as shelve
        
db = shelve.open("data.db")
db["key"] = "value"
db.close()
```