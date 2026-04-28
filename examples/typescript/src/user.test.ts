import { UserService } from "./user"

describe("UserService", () => {
  it("runs", () => {
    expect(new UserService().run()).toBe("ok")
  })
})
