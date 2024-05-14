from kivy.lang import Builder  # type: ignore
from kivy.properties import (  # type: ignore
    StringProperty, ColorProperty, ObjectProperty
)
from kivymd.uix.appbar import MDTopAppBar  # type: ignore
from kivymd.app import MDApp  # type: ignore
from kivymd.uix.navigationdrawer import (  # type: ignore
    MDNavigationDrawerItem, MDNavigationDrawerItemTrailingText
)
from kivymd.uix.screen import MDScreen  # type: ignore
from kivy.uix.popup import Popup  # type: ignore
from kivy.clock import Clock  # type: ignore
from kivy.app import App  # type: ignore
from device import TelebrellaDevice
import json


class DrawerItem(MDNavigationDrawerItem):
    icon = StringProperty()
    text = StringProperty()
    trailing_text = StringProperty()
    trailing_text_color = ColorProperty()
    _trailing_text_obj = None
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()

    def on_trailing_text(self, instance, value) -> None:
        self._trailing_text_obj = MDNavigationDrawerItemTrailingText(
            text=value,
            theme_text_color="Custom",
            text_color=self._trailing_text_obj
        )
        self.add_widget(self._trailing_text_obj)

    def on_trailing_text_color(self, instance, value) -> None:
        if self._trailing_text_obj is not None:
            self._trailing_text_obj.text_color = value


class Options(MDScreen):
    nav_drawer = ObjectProperty()


class Controls(MDScreen):
    nav_drawer = ObjectProperty()


class AppScreen(MDScreen):
    pass


class SettingChange(Popup):
    configs = {
        "Open": {"text": "Umbrella is opening...", "duration": 5},
        "Close": {"text": "Umbrella is closing...", "duration": 5},
        "Windsensor_ON": {"text": "Wind sensor is now on.", "duration": 2},
        "Windsensor_OFF": {"text": "Wind sensor is now off.", "duration": 2}
    }

    def __init__(self, pop_type: str, **kwargs) -> None:
        super(SettingChange, self).__init__(auto_dismiss=False, **kwargs)
        Clock.schedule_once(
            lambda x: self.dismiss(),
            self.configs[pop_type]['duration'])
        self.ids.popup_text.text = self.configs[pop_type]['text']


class AppBarDisplay(MDTopAppBar):
    nav_drawer = ObjectProperty()

    def cycle_device(self) -> None:
        app = App.get_running_app()
        app.device_index += 1
        if app.device_index >= len(app.devices):
            app.device_index = 0
        self.ids.device_id.text = "Telebrella Controls: Device #" + str(
            app.device_index + 1)
        print(app.device_focus.uuid)


class MainApp(MDApp):
    '''The main app
    '''
    __configs_file = "configs.json"
    with open(__configs_file, 'r') as f:
        __configs: dict = json.load(f)
    devices = [TelebrellaDevice(**device)
               for device in __configs['devices']]

    def build(self):
        self.theme_cls.secondaryContainerColor = "teal"
        self.device_index = 0
        return Builder.load_file("layout.kv")

    @property
    def device_focus(self) -> TelebrellaDevice:
        return self.devices[self.device_index]

    def cycle_device(self):
        current_index = next((index
                              for index, device in enumerate(self.devices)
                              if device.uuid == self.device_focus.uuid))
        if current_index != len(self.devices) - 1:
            new_index = current_index + 1
        else:
            new_index = 0
        self.device_focus = self.devices[new_index]
        print(self.root.ids)

    def display_popup(self, type: str) -> None:
        SettingChange(pop_type=type).open()

    def open_umbrella(self) -> None:
        self.display_popup(type="Open")
        self.device_focus.is_open = True

    def close_umbrella(self) -> None:
        self.display_popup(type="Close")
        self.device_focus.is_open = False

    def toggle_windsensor(self) -> None:
        self.device_focus.windsensor_on = not self.device_focus.windsensor_on


if __name__ == "__main__":
    MainApp().run()
