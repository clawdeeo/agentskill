using Example.Core;

namespace Example.App;

public class App {
    public void Start() {
        new UserService().Run();
    }
}
