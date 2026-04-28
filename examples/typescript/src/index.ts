import { UserService } from "./user"

export function runApp() {
  return new UserService().run()
}
