import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'

config.global.plugins = config.global.plugins || []
config.global.plugins.push(ElementPlus)
