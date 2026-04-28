package com.example;

import com.example.service.UserService;

public class App {
    public void start() {
        new UserService().run();
    }
}
